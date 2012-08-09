# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden,\
    HttpResponseNotFound
from django.utils import simplejson as json

from wiki.core.exceptions import NoRootURL

def json_view(func):
    def wrap(request, *args, **kwargs):
        obj = func(request, *args, **kwargs)
        data = json.dumps(obj, ensure_ascii=False)
        status = kwargs.get('status', 200)
        response = HttpResponse(mimetype='application/json', status=status)
        response.write(data)
        return response
    return wrap

def get_article(func=None, can_read=True, can_write=False):
    """Intercepts the keyword args path or article_id and looks up an article,
    calling the decorated func with this ID."""
    
    def the_func(request, *args, **kwargs):
        import models

        path = kwargs.pop('path', None)
        article_id = kwargs.pop('article_id', None)
        
        if can_read:
            articles = models.Article.objects.can_read(request.user)
        if can_write:
            articles = models.Article.objects.can_write(request.user)
        
        # TODO: Is this the way to do it?
        articles = articles.select_related()
        
        urlpath = None
        if article_id:
            article = get_object_or_404(articles, id=article_id)
            try:
                urlpath = models.URLPath.objects.get(articles=article)
            except models.URLPath.DoesNotExist, models.URLPath.MultipleObjectsReturned:
                urlpath = None
        else:
            try:
                urlpath = models.URLPath.get_by_path(path, select_related=True)
            except NoRootURL:
                return redirect('wiki:root_create')
            except models.URLPath.DoesNotExist:
                try:
                    pathlist = filter(lambda x: x!="", path.split("/"),)
                    path = "/".join(pathlist[:-1])
                    parent = models.URLPath.get_by_path(path)
                    return redirect(reverse("wiki:create_url", args=(parent.path,)) + "?slug=%s" % pathlist[-1])
                except models.URLPath.DoesNotExist:
                    # TODO: Make a nice page
                    return HttpResponseNotFound("This article was not found, and neither was the parent. This page should look nicer.")
            # TODO: If the article is not found but it exists, there is a permission error!
            article = get_object_or_404(articles, id=urlpath.article.id)
        
        kwargs['urlpath'] = urlpath
        
        return func(request, article, *args, **kwargs)
    
    if func:
        return the_func
    else:
        return lambda func: get_article(func, can_read=can_read, can_write=can_write)

