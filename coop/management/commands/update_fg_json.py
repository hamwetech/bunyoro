import argparse
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from coop.models import CooperativeMember, FarmerGroup
from django.db.models import Avg, Max, Min, Sum, Count


class Command(BaseCommand):  # pragma: no cover
    help = "Updates consent status for each user"

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=argparse.FileType('r'))

    def handle(self, *args, **options):

        model = CooperativeMember
        # file_path = "data.txt"
        file_path = options['file_path']

        # Open the file in read mode
        # with open(file_path, "r") as file:
        #     data = file.read()
        count = 0
        for text in file_path:
            start_index = text.find("<QueryDict: ") + len("<QueryDict: ")
            end_index = text.rfind(">")  # Finds the last occurrence of ">"

            extracted_text = text[start_index:end_index]

            # print(extracted_text)
            start_index = text.find("<QueryDict: ") + len("<QueryDict: ")
            end_index = text.rfind(">")  # Finds the last occurrence of ">"

            extracted_text = str(text[start_index:end_index])
            extracted_text = extracted_text.replace("u'", "'")
            extracted_text = extracted_text.replace("[", "")
            extracted_text = extracted_text.replace("]", "")

            start_index2 = extracted_text.find("'image")
            end_index2 = extracted_text.rfind(")>,")  # Finds the last occurrence of ">"
            extracted_text2 = str(extracted_text[start_index2:end_index2])
            # print(extracted_text2)
            extracted_text = extracted_text.replace(", %s)>" % extracted_text2, "")


            import ast
            import json
            # print(eval(extracted_text))
            data_dict = eval(extracted_text.strip())
            farmer_group = data_dict['farmer_group']
            surname = data_dict['surname']
            other_name = data_dict['other_name']
            first_name = data_dict['first_name']
            gps_coodinates = data_dict['gps_coodinates']

            ffgg = None
            fgs = FarmerGroup.objects.filter(pk=farmer_group)
            if fgs.exists():
                ffgg = fgs[0]

            # member = CooperativeMember.objects.filter(first_name=first_name, surname=surname,other_name=other_name,gps_coodinates=gps_coodinates)
            member = CooperativeMember.objects.filter(first_name=first_name, surname=surname, other_name=other_name).update(farmer_group=ffgg)

            count += 1
            print("Updated. %s " % (count))

            # if member.exists():
            #     member = member[0]
            #
            #         member.farmer_group=fgs
            #         member.save()

            # try:
            #
            #
            #     print(type(extracted_text))
            # except Exception as e:
            #     import traceback
            #     print(traceback.format_exc())