import logging
import time
from rest_framework import serializers

from wallets.models import Transaction, Wallet


logger = logging.getLogger(__name__)


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ("uuid", "balance")
        read_only_fields = ("uuid", "balance")


class TransactionSerializer(serializers.ModelSerializer):
    uuid = serializers.UUIDField(write_only=True)

    class Meta:
        model = Transaction
        fields = ("amount", "uuid")

    def validate(self, attrs):
        wallet_uuid = attrs.get('uuid')
        if wallet_uuid:
            try:
                Wallet.objects.get(uuid=wallet_uuid)
            except Wallet.DoesNotExist:
                raise serializers.ValidationError(f"Wallet with UUID {wallet_uuid} does not exist.")
        else:
            raise serializers.ValidationError("Wallet UUID is required.")
        return attrs


class DepositTransactionSerializer(TransactionSerializer):
    pass


class WithdrawalTransactionSerializer(TransactionSerializer):
    timestamp = serializers.FloatField()

    class Meta:
        model = Transaction
        fields = ("amount", "timestamp", "uuid")

    def validate_timestamp(self, value):
        if value <= time.time():
            raise serializers.ValidationError("The timestamp must be in the future.")
        return value
