import uuid
import time
import random
import logging

from django.db import models, transaction
from django.db import IntegrityError

logger = logging.getLogger(__name__)


def generate_random_integer():
    return random.randint(10000, 99999)


class Wallet(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    balance = models.BigIntegerField(default=0)


class Transaction(models.Model):
    amount = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    wallet = models.ForeignKey(Wallet, on_delete=models.SET_NULL, related_name='transactions', null=True)
    followup_id = models.IntegerField(default=generate_random_integer)
    success = models.BooleanField(default=False)


def create_deposit_transaction(wallet_uuid, amount):
    transaction_object = None
    with transaction.atomic():
        try:
            wallet = Wallet.objects.select_for_update().get(uuid=wallet_uuid)
            wallet.balance += amount
            wallet.save()
            transaction_object = Transaction.objects.create(
                amount=amount, created_at=time.time(), wallet=wallet, success=True)
        except IntegrityError as ie:
            logger.error(f'Integrity error at create_deposit_transaction: {str(ie)}')

    return transaction_object
