# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from account.models import AccountTransaction
from django.views.generic import ListView, DetailView


class TransactionListView(ListView):
    model = AccountTransaction
