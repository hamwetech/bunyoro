from __future__ import unicode_literals
import os
import magic
import re
import xlrd
import xlwt
import json
import datetime
from django.db import transaction
from django.shortcuts import render, redirect, HttpResponse
from django.urls import reverse_lazy
from django.db.models import Q, CharField, Max, Value as V
from django.utils.encoding import smart_str
from django.forms.formsets import formset_factory, BaseFormSet
from django.views.generic import ListView, DetailView, View
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from coop.forms import SavingsForm, SeasonForm
from coop.views.member import save_transaction

from coop.models import Savings, Season
from conf.utils import generate_alpanumeric, genetate_uuid4, log_error, log_debug, generate_numeric, float_to_intstring, get_deleted_objects,\
get_message_template as message_template


class ExtraContext(object):
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ExtraContext, self).get_context_data(**kwargs)

        context.update(self.extra_context)
        return context


class SavingsListView(ExtraContext, ListView):
    model = Savings
    ordering = ['-create_date']
    extra_context = {'active': ['_savings']}

    def dispatch(self, *args, **kwargs):
        if self.request.GET.get('download'):
            return self.download_file()
        return super(SavingsListView, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super(SavingsListView, self).get_queryset()
        return queryset


class SavingsCreateView(CreateView):
    model = Savings
    form_class = SavingsForm
    success_url = reverse_lazy('coop:savings_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.reference = generate_alpanumeric(size=16)
        if form.instance.member:
            balance = form.instance.member.savings_balance
            new_balance = balance + form.instance.amount
            form.instance.member.savings_balance = new_balance
            form.instance.member.save()

        if not form.instance.member and form.instance.farmer_group:
            balance = form.instance.farmer_group.savings_balance
            new_balance = balance + form.instance.amount
            form.instance.farmer_group.savings_balance = new_balance
            form.instance.farmer_group.savings_balance.save()
        form.instance.balance_after = new_balance
        return super(SavingsCreateView, self).form_valid(form)


class SavingsUpdateView(UpdateView):
    model = Savings
    form_class = SavingsForm
    success_url = reverse_lazy('coop:savings_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super(SavingsUpdateView, self).form_valid(form)


class SavingsDeleteView(DeleteView):
    model = Savings
    success_url = reverse_lazy('coop:savings_list')

    def get_context_data(self, **kwargs):
        #
        context = super(SavingsDeleteView, self).get_context_data(**kwargs)
        #
        deletable_objects, model_count, protected = get_deleted_objects([self.object])
        #
        context['deletable_objects'] = deletable_objects
        context['model_count'] = dict(model_count).items()
        context['protected'] = protected
        #
        return context


#
class SeasonFormListView(ExtraContext, ListView):
    model = Season
    ordering = ['-create_date']
    extra_context = {'active': ['_season']}

    def dispatch(self, *args, **kwargs):
        if self.request.GET.get('download'):
            return self.download_file()
        return super(SeasonFormListView, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        queryset = super(SeasonFormListView, self).get_queryset()
        return queryset


class SeasonCreateView(CreateView):
    model = Season
    form_class = SeasonForm
    success_url = reverse_lazy('coop:season_list')


class SeasonUpdateView(SeasonCreateView, UpdateView):
    pass


class SeasonDeleteView(DeleteView):
    model = Season
    success_url = reverse_lazy('coop:season_list')

    def get_context_data(self, **kwargs):
        #
        context = super(SavingsDeleteView, self).get_context_data(**kwargs)
        #
        deletable_objects, model_count, protected = get_deleted_objects([self.object])
        #
        context['deletable_objects'] = deletable_objects
        context['model_count'] = dict(model_count).items()
        context['protected'] = protected
        #
        return context