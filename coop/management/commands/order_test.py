from __future__ import unicode_literals
import json
from django.db import transaction
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.forms.formsets import formset_factory, BaseFormSet
from django.views.generic import ListView, DetailView, View
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.models import User

from coop.models import MemberOrder, CooperativeMember
from coop.forms import OrderItemForm, MemberOrderForm
from coop.views.member import save_transaction
from conf.utils import generate_alpanumeric, genetate_uuid4, log_error, log_debug, generate_numeric, float_to_intstring, get_deleted_objects,\
get_message_template as message_template
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from conf.utils import generate_numeric
from coop.models import CooperativeMember

class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        member = CooperativeMember.objects.all()[:454]
        count = 1
        for m in member:
            t = datetime.now()
            import random
            n1 = random.sample(xrange(1,10), 4)
            n2 = random.sample(xrange(4,6), 2)
            numbers = [n1i * 10**n2i for n1i, n2i in zip(n1, n2)]
            print(numbers[0])
            MemberOrder.objects.create(
                cooperative = m.cooperative,
                member = m,
                order_reference = generate_numeric(8, '30'), 
                order_price = numbers[0], 
                status = 'PENDING',
                order_date = t,
                created_by = User.objects.get(pk=1)
            )
