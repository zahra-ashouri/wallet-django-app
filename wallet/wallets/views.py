from http import HTTPStatus
import logging

from django.utils import timezone
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.serializers import ValidationError

from wallets.models import Wallet, create_deposit_transaction
from wallets.serializers import WalletSerializer, DepositTransactionSerializer, WithdrawalTransactionSerializer
from wallets.tasks import withdraw


logger = logging.getLogger(__name__)


class CreateWalletView(CreateAPIView):
    serializer_class = WalletSerializer

    def perform_create(self, serializer):
        serializer.save()


class RetrieveWalletView(RetrieveAPIView):
    serializer_class = WalletSerializer
    queryset = Wallet.objects.all()
    lookup_field = "uuid"


class CreateDepositView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            data.update(kwargs)
            serializer = DepositTransactionSerializer(data=data)
            serializer.is_valid(raise_exception=True)

            transaction = create_deposit_transaction(wallet_uuid=data["uuid"], amount=data["amount"])
            if transaction:
                return Response({'data': 'Successful',
                                 'followup_id': transaction.followup_id},
                                status=HTTPStatus.CREATED)
            else:
                return Response({'data': 'Failure! Please try again'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        except ValidationError as ve:
            logger.error(f'Validation error at creating deposit transaction: {str(ve)}')
            return Response({'data': 'Bad Request'}, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            logger.error(f'Exception at creating deposit transaction: {str(e)}')
            return Response({'data': 'Internal Error'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


class ScheduleWithdrawView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            data.update(kwargs)
            serializer = WithdrawalTransactionSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            amount = serializer.validated_data['amount']
            wallet_uuid = serializer.validated_data['uuid']
            timestamp = data.get('timestamp')

            schedule_time = timezone.datetime.fromtimestamp(timestamp)
            withdraw.apply_async((wallet_uuid, amount), eta=schedule_time)

            return Response({'data': 'Withdrawal scheduled successfully'}, status=HTTPStatus.CREATED)

        except ValidationError as ve:
            logger.error(f'Validation error at creating withdrawal task: {str(ve)}')
            return Response({'data': 'Bad Request'}, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            logger.error(f'Exception at creating withdrawal task: {str(e)}')
            return Response({'data': 'Internal Error'}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
