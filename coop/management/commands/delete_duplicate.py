from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from coop.models import CooperativeMember
from django.db.models import Avg, Max, Min, Sum, Count


class Command(BaseCommand):  # pragma: no cover
    help = "Updates consent status for each user"

    def handle(self, *args, **options):

        model = CooperativeMember
        fields = ['first_name', 'surname', 'other_name', 'phone_number', 'date_of_birth']
        """
        Removes records from `model` duplicated on `fields`
        while leaving the most recent one (biggest `id`).
        """
        duplicates = model.objects.values(*fields)

        # override any model specific ordering (for `.annotate()`)
        duplicates = duplicates.order_by()

        # group by same values of `fields`; count how many rows are the same
        duplicates = duplicates.annotate(
            max_id=Max("id"), count_id=Count("id")
        )

        # leave out only the ones which are actually duplicated
        duplicates = duplicates.filter(count_id__gt=1)

        for duplicate in duplicates:
            to_delete = model.objects.filter(**{x: duplicate[x] for x in fields})
            print(to_delete)

            # leave out the latest duplicated record
            to_delete = to_delete.exclude(id=duplicate["max_id"])

            to_delete.delete()
