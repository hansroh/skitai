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
from rs4.webkit.djadmin import set_title, ModelAdmin, StackedInline, CountFilter, NullFilter
from django.template.defaultfilters import truncatechars

import os


# firebase user model -----------------------------------
from .models import Transcription, TranscriptionLog

@admin.register(Transcription)
class TranscriptionAdmin (ModelAdmin):
    list_display = ("task_id", "last_status", "created", "last_updated")
    readonly_fields = ('created', 'last_updated')


@admin.register(TranscriptionLog)
class TranscriptionLogAdmin (ModelAdmin):
    list_display = ("transcription", "status", "created")

    def get_queryset (self, request):
        return super ().get_queryset (request).select_related ('transcription')
