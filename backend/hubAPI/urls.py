from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from .views import (MyTokenObtainPairView, MyTokenRefreshView, TransactionAPIView, get_saving_plans, get_transactions,
                    get_routes, create_user, WalletAPIView, LabelAPIView, ImportInvoicesAPIView, SavingPlanAPIView)

urlpatterns = [
    path('', get_routes),
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', MyTokenRefreshView.as_view(), name='token_refresh'),
    path('register/', create_user, name='create_user'),
    path('wallet/', WalletAPIView.as_view(), name='wallet'),
    path('labels/', LabelAPIView.as_view(), name='labels'),
    path('label/', LabelAPIView.as_view(), name='label'),
    path('labels/<int:label_pk>', LabelAPIView.as_view(), name='label'),
    path('label/<int:label_pk>', LabelAPIView.as_view(), name='label_singular'),
    path('savingplans/', SavingPlanAPIView.as_view(), name='saving_plans'),
    path('savingplan/', SavingPlanAPIView.as_view(), name='saving_plan'),
    path('savingplans/<int:saving_plan_pk>', SavingPlanAPIView.as_view(), name='saving_plan_detail'),
    path('savingplan/<int:saving_plan_pk>', SavingPlanAPIView.as_view(), name='saving_plan_detail_singular'),
    path('transactions/', get_transactions, name='transactions'),
    path('transaction/', TransactionAPIView.as_view(), name='transaction'),
    path('transaction/<int:transaction_pk>', TransactionAPIView.as_view(), name='transaction'),
    path('import/', ImportInvoicesAPIView.as_view(), name='import')
]
