# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-10-05 09:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0007_auto_20160826_1327'),
    ]

    operations = [
        migrations.AddField(
            model_name='individual',
            name='review_status',
            field=models.CharField(blank=True, choices=[(b'A', b'Accepted'), (b'E', b'Accepted - Exome'), (b'G', b'Accepted - Genome'), (b'R', b'Not Accepted'), (b'N', b'See Notes'), (b'H', b'Hold')], default=b'', max_length=1, null=True),
        ),
    ]