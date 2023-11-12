"""models for App called Preferences"""
from urllib.parse import parse_qs

from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_delete, post_save


def url_parm_encode(**kwargs):
    """function too translate url paramaters from GET request in dictionary to hash string"""
    kwargs = {
        k: ",".join(v if type(v) is list else [v]).split(",") for k, v in kwargs.items()
    }
    kwargs = {k: [v] if type(v) is str else v for k, v in kwargs.items()}
    kwargs_hash = "articles_" + str(
        {k.lower(): [i.lower() for i in sorted(v)] for k, v in kwargs.items()}
    )
    kwargs_hash = "".join([i if i.isalnum() else "_" for i in kwargs_hash])
    return kwargs_hash, kwargs


def get_pages(recache=False):
    """function to get page section html"""
    pages_html = cache.get("pages_html")

    if pages_html is None or recache:
        all_pages = Page.objects.all().order_by("position_index")
        TEMPLATE = (
            '<a id="{id}" class="nav-button btn btn-sm rounded-5 p-1 px-3 mx-1 mb-1'
            ' shadow-sm bg-dark-subtle text-dark" tabindex="{idx}"'
            ' href="/?{url}">{name}</a>'
        )
        pages_html = ""
        for page in all_pages:
            url_parameters = parse_qs(page.url_parameters)
            kwargs_hash, _ = url_parm_encode(**url_parameters)
            pages_html += TEMPLATE.format(
                id=kwargs_hash,
                idx=page.position_index,
                url=page.url_parameters,
                name=page.html_icon + page.name,
            )

        cache.set("pages_html", pages_html, 60 * 60 * 48)

    return pages_html


# Create your models here.
class Page(models.Model):
    """model for page sections"""

    name = models.CharField(max_length=40, default="USA")
    url_parameters = models.CharField(
        max_length=500,
        default="publisher__name=financial+times,bloomberg&categories=usa&content_type=article",
    )
    html_icon = models.TextField(default="#", blank=True)
    position_index = models.SmallIntegerField()

    def __str__(self):
        """display/string repreesentation of individual element"""
        if "<" in self.html_icon:
            return f"[ICON]{self.name}"
        else:
            return f"{self.html_icon}{self.name}"

    @staticmethod
    def update_cached_html(sender, instance, **kwargs):
        _ = get_pages(recache=True)


post_save.connect(Page.update_cached_html, sender=Page)
post_delete.connect(Page.update_cached_html, sender=Page)
