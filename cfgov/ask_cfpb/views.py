import json
from urllib.parse import urljoin

from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.defaultfilters import slugify
from haystack.query import SearchQuerySet

from wagtail.core.models import Site
from wagtailsharing.models import SharingSite
from wagtailsharing.views import ServeView

from bs4 import BeautifulSoup as bs

from ask_cfpb.models import AnswerPage, AnswerResultsPage, AskSearch


def annotate_links(answer_text):
    """
    Parse and annotate links from answer text.

    Return the annotated answer
    and an enumerated list of links as footnotes.
    """
    try:
        _site = Site.objects.get(is_default_site=True)
    except Site.DoesNotExist:
        raise RuntimeError('no default wagtail site configured')

    footnotes = []
    soup = bs(answer_text, 'lxml')
    links = soup.findAll('a')
    index = 1
    for link in links:
        if not link.get('href'):
            continue
        footnotes.append(
            (index, urljoin(_site.root_url, link.get('href'))))
        parent = link.parent
        link_location = parent.index(link)
        super_tag = soup.new_tag('sup')
        super_tag.string = str(index)
        parent.insert(link_location + 1, super_tag)
        index += 1
    return (str(soup), footnotes)


def view_answer(request, slug, language, answer_id):
    answer_page = get_object_or_404(
        AnswerPage, language=language, answer_base__id=answer_id)
    if answer_page.live is False:
        raise Http404
    if answer_page.redirect_to_page:
        new_page = answer_page.redirect_to_page
        return redirect(new_page.url, permanent=True)
    if "{}-{}-{}".format(slug, language, answer_id) != answer_page.slug:
        return redirect(answer_page.url, permanent=True)

    # We don't want to call answer_page.serve(request) here because that
    # would bypass wagtail-sharing logic that allows for review of draft
    # revisions via a sharing site.
    try:
        sharing_site = SharingSite.find_for_request(request)
    except SharingSite.DoesNotExist:
        return answer_page.serve(request)

    page, args, kwargs = ServeView.route(
        sharing_site.site,
        request,
        request.path
    )

    return ServeView.serve(page, request, args, kwargs)


def ask_search(request, language='en', as_json=False):
    if 'selected_facets' in request.GET:
        return redirect_ask_search(request, language=language)
    language_map = {
        'en': 'ask-cfpb-search-results',
        'es': 'respuestas'
    }
    results_page = get_object_or_404(
        AnswerResultsPage,
        language=language,
        slug=language_map[language]
    )

    # If there's no query string, don't search
    search_term = request.GET.get('q', '')
    if not search_term:
        results_page.query = ''
        results_page.result_query = ''
        return results_page.serve(request)

    search = AskSearch(search_term=search_term, language=language)
    if search.queryset.count() == 0:
        search.suggest(request=request)

    if as_json:
        results = {
            'query': search_term,
            'result_query': search.search_term,
            'suggestion': search.suggestion,
            'results': [
                {
                    'question': result.autocomplete,
                    'url': result.url,
                    'text': result.text,
                    'preview': result.preview,
                }
                for result in search.queryset
            ]
        }
        json_results = json.dumps(results)
        return HttpResponse(json_results, content_type='application/json')

    results_page.query = search_term
    results_page.result_query = search.search_term
    results_page.suggestion = search.suggestion
    results_page.answers = [
        (result.url, result.autocomplete, result.preview)
        for result in search.queryset
    ]
    return results_page.serve(request)


def ask_autocomplete(request, language='en'):
    term = request.GET.get(
        'term', '').strip().replace('<', '')
    if not term:
        return JsonResponse([], safe=False)

    try:
        sqs = SearchQuerySet().models(AnswerPage)
        sqs = sqs.autocomplete(
            autocomplete=term,
            language=language
        )
        results = [{'question': result.autocomplete,
                    'url': result.url}
                   for result in sqs[:20]]
        return JsonResponse(results, safe=False)
    except IndexError:
        return JsonResponse([], safe=False)


def redirect_ask_search(request, language='en'):
    """
    Redirect legacy knowledgebase requests built via query strings.

    Prior to 2016, Ask CFPB (knowledgebase) built category, audience and
    search-tag pages based on query string facets. When Ask was migrated
    to Wagtail, we simplified the page structure and left this view
    to route legacy requests using the old query string faceting routine.

    Knowledgebase used /askcfpb/ (no hyphen) as its base URL node.

    If the legacy query string has no 'q' element or a blank one, we return
    the current base /ask-cfpb/search/ page.
    If the query string has a 'q' query, we'll run that search.
    Otherwise, we look for legacy faceting.

    We want to catch these search facets, in this order:
    - selected_facets=category_exact:
    - selected_facets=audience_exact
    - selected_facets=tag_exact:
    """
    category_facet = 'category_exact:'
    audience_facet = 'audience_exact:'
    tag_facet = 'tag_exact:'
    if request.GET.get('q'):
        querystring = request.GET.get('q').strip()
        if not querystring:
            return redirect('/ask-cfpb/search/', permanent=True)
        return redirect(
            '/ask-cfpb/search/?q={query}'.format(
                query=querystring), permanent=True)
    else:
        facets = request.GET.getlist('selected_facets')
        if not facets or not facets[0]:
            return redirect(
                '/ask-cfpb/search/', permanent=True)

        def redirect_to_category(category, language):
            if language == 'es':
                return redirect(
                    '/es/obtener-respuestas/categoria-{category}/'.format(
                        category=category), permanent=True)
            return redirect(
                '/ask-cfpb/category-{category}/'.format(
                    category=category), permanent=True)

        def redirect_to_audience(audience):
            """We currently only offer audience pages to English users."""
            return redirect(
                '/ask-cfpb/audience-{audience}/'.format(
                    audience=audience), permanent=True)

        def redirect_to_tag(tag, language):
            """Handle tags passed with underscore separators."""
            if language == 'es':
                return redirect(
                    '/es/obtener-respuestas/buscar-por-etiqueta/{tag}/'.format(
                        tag=tag), permanent=True)
            else:
                return redirect(
                    '/ask-cfpb/search-by-tag/{tag}/'.format(
                        tag=tag), permanent=True)

        # Redirect by facet value, if there is one, starting with category.
        # We want to exhaust facets each time, so we need three loops.
        # We act only on the first of any facet type found.
        # Most search redirects will find a category and return.
        for facet in facets:
            if category_facet in facet:
                category = facet.replace(category_facet, '')
                if category:
                    slug = slugify(category)  # handle uppercase and spaces
                    return redirect_to_category(slug, language)

        for facet in facets:
            if audience_facet in facet:
                audience_raw = facet.replace(audience_facet, '')
                if audience_raw:
                    audience = slugify(audience_raw.replace('+', '-'))
                    return redirect_to_audience(audience)

        for facet in facets:
            if tag_facet in facet:
                raw_tag = facet.replace(tag_facet, '')
                if raw_tag:
                    tag = raw_tag.replace(
                        ' ', '_').replace(
                        '%20', '_').replace(
                        '+', '_')
                    return redirect_to_tag(tag, language)

        raise Http404
