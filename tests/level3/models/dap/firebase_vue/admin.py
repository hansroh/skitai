from django.contrib import admin
from django.conf import settings
from django.urls import path, reverse
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.db.models import Q, F, Count, Sum, Avg, Max, Min, StdDev, Variance
from django.contrib.admin import DateFieldListFilter, SimpleListFilter
from django.utils.html import format_html
from rangefilter.filter import DateRangeFilter, DateTimeRangeFilter
from admin_numeric_filter.admin import NumericFilterModelAdmin, SingleNumericFilter, RangeNumericFilter, SliderNumericFilter
from atila.collabo.django.admin import set_title, ModelAdmin, StackedInline, CountFilter, NullFilter
from django.template.defaultfilters import truncatechars

import os
set_title ('Atila-Vue Management')

# firebase user model -----------------------------------
from .models import User, UserLog

@admin.register(User)
class UserAdmin (ModelAdmin):
    list_display = ("uid", "provider", "email", "nick_name", "grp", "status", "email_verified", "created", "last_updated")
    readonly_fields = ('salt', 'signature')


@admin.register(UserLog)
class UserLogAdmin (ModelAdmin):
    list_display = ("user", "action", "created")

    def get_queryset (self, request):
        return super ().get_queryset (request).select_related ('user')
