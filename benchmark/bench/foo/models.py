from django.db import models

class Foo(models.Model):
    id = models.AutoField(primary_key=True)
    tx_id = models.CharField(unique=True, max_length=1024, blank=True, null=True)
    from_left = models.BigIntegerField()
    to_left = models.BigIntegerField()
    amount = models.BigIntegerField()
    from_address = models.CharField(max_length=256, blank=True, null=True)
    to_address = models.CharField(max_length=256, blank=True, null=True)
    detail = models.CharField(max_length=1024)
    created_at = models.DateTimeField(auto_now_add = True)
    from_wallet_id = models.BigIntegerField()
    to_wallet_id = models.BigIntegerField()
    valid = models.CharField(max_length=16)
    block_number = models.BigIntegerField(blank=True, null=True)
    push_token = models.CharField(max_length=256, blank=True, null=True)
    errcode = models.IntegerField(blank=True, null=True)
    errmsg = models.CharField(max_length=1024, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'foo'
