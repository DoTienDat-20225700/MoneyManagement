from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from .reports_views import ReportSummaryAPIView, ReportTransactionsAPIView, ReportExportCSVAPIView
from .views import (MyTokenObtainPairView, MyTokenRefreshView, TransactionAPIView, get_saving_plans, get_transactions,
                    get_routes, create_user, WalletAPIView, LabelAPIView, ImportInvoicesAPIView, SavingPlanAPIView,
                    SavingPlanContributionAPIView, BudgetAPIView, BudgetSummaryAPIView)

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
    path('savingplans/<int:saving_plan_pk>/contributions/', SavingPlanContributionAPIView.as_view(), name='saving_plan_contributions'),
    path('savingplan/<int:saving_plan_pk>/contributions/', SavingPlanContributionAPIView.as_view(), name='saving_plan_contributions_singular'),
    path('savingplans/<int:saving_plan_pk>/contributions/<int:contribution_pk>', SavingPlanContributionAPIView.as_view(), name='saving_plan_contribution_detail'),
    path('savingplans/<int:saving_plan_pk>/contributions/<int:contribution_pk>/', SavingPlanContributionAPIView.as_view(), name='saving_plan_contribution_detail_slash'),
    path('savingplan/<int:saving_plan_pk>/contributions/<int:contribution_pk>', SavingPlanContributionAPIView.as_view(), name='saving_plan_contribution_detail_singular'),
    path('savingplan/<int:saving_plan_pk>/contributions/<int:contribution_pk>/', SavingPlanContributionAPIView.as_view(), name='saving_plan_contribution_detail_singular_slash'),
    path('budgets/', BudgetAPIView.as_view(), name='budgets'),
    path('budget/', BudgetAPIView.as_view(), name='budget'),
    path('budgets/summary/', BudgetSummaryAPIView.as_view(), name='budgets_summary'),
    path('budget/summary/', BudgetSummaryAPIView.as_view(), name='budget_summary_singular'),
    path('budgets/<int:budget_pk>', BudgetAPIView.as_view(), name='budget_detail'),
    path('budget/<int:budget_pk>', BudgetAPIView.as_view(), name='budget_detail_singular'),
    path('reports/summary/', ReportSummaryAPIView.as_view(), name='reports_summary'),
    path('reports/transactions/', ReportTransactionsAPIView.as_view(), name='reports_transactions'),
    path('reports/export/csv/', ReportExportCSVAPIView.as_view(), name='reports_export_csv'),
    path('transactions/', get_transactions, name='transactions'),
    path('transaction/', TransactionAPIView.as_view(), name='transaction'),
    path('transaction/<int:transaction_pk>', TransactionAPIView.as_view(), name='transaction'),
    path('import/', ImportInvoicesAPIView.as_view(), name='import')
]
