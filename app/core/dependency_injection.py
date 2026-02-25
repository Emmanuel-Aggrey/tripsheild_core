from app.general.service import GeneralService
from app.insuranc_records.services import InsuranceRecordService
from app.accounts.services import AccountService
from app.packages.services import PackageService
from app.payment.services import PaymentService
from app.claims.services import ClaimService
from app.core.services import CoreService


class SERVICE_NAMES:
    GeneralService = "general_service"
    ChatService = "chat_service"
    InsuranceRecordService = "insurance_record_service"
    AccountService = "account_service"
    PackageService = "package_service"
    PaymentService = "payment_service"
    ClaimService = "claim_service"
    CoreService = "core_service"


class ServiceLocator:
    service = {}

    general_service: GeneralService
    insurance_record_service: InsuranceRecordService
    account_service: AccountService
    package_service: PackageService
    payment_service: PaymentService
    claim_service: ClaimService
    core_service: CoreService

    def __init__(self):
        self._services = {}

    def register(self, name, service):
        self._services[name] = service

    def get(self, name):
        return self._services[name]

    def __getitem__(self, name):
        return self.get(name)

    def __getattr__(self, name):
        return self.get(name)


#  register services


service_locator = ServiceLocator()

service_locator.register(SERVICE_NAMES.GeneralService, GeneralService())
service_locator.register(
    SERVICE_NAMES.InsuranceRecordService, InsuranceRecordService())
service_locator.register(SERVICE_NAMES.AccountService, AccountService())
service_locator.register(SERVICE_NAMES.PackageService, PackageService())
service_locator.register(SERVICE_NAMES.PaymentService, PaymentService())
service_locator.register(SERVICE_NAMES.ClaimService, ClaimService())
service_locator.register(SERVICE_NAMES.CoreService, CoreService())
