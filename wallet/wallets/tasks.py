import logging
from http import HTTPStatus

from celery import shared_task
from django.db import transaction

from wallets.models import Wallet, Transaction
from wallets.utils import request_third_party_deposit


logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 5, 'countdown': 10})
def withdraw(self, wallet_uuid, amount):
    try:
        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(uuid=wallet_uuid)

            if wallet.balance < amount:
                logger.warning(
                    f"Insufficient balance for wallet {wallet_uuid}. Current balance: {wallet.balance}, attempted withdrawal: {amount}")
                return {'status': 'failure', 'message': 'Insufficient balance'}

            wallet.balance -= amount
            wallet.save()

            Transaction.objects.create(wallet=wallet, amount=amount, success=True)

        bank_response = request_third_party_deposit()

        if not bank_response or (bank_response and bank_response.get('status') != HTTPStatus.OK):
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(uuid=wallet_uuid)
                wallet.balance += amount
                wallet.save()

                last_transaction = Transaction.objects.select_for_update().filter(
                    wallet__uuid=wallet_uuid).order_by('-created_at').first()
                last_transaction.success = False
                last_transaction.save()
                raise Exception('Third party app failed to deposit into the account!')

        return {'status': 'success', 'message': 'Withdrawal successful'}

    except Wallet.DoesNotExist:
        logger.error(f"Wallet with UUID {wallet_uuid} does not exist.")
        return {'status': 'failure', 'message': f'Wallet with UUID {wallet_uuid} does not exist.'}
    except Exception as e:
        logger.error(f"Error during withdrawal for wallet {wallet_uuid}: {str(e)}")
        raise e
