from django.urls import path

from ideas.views import (
    BusinessPlanDetailView,
    BusinessPlanListView,
    BusinessPlanSoftDeleteView,
    GenerateBusinessPlanView,
    IdeaAnalysisView,
    IdeaDeleteView,
    IdeaDetailView,
    MyIdeasListView,
    UpdateReportStepsView,
)

urlpatterns = [
    path("analyze-create/", IdeaAnalysisView.as_view(), name="idea-analysis"),
    path("my-ideas/", MyIdeasListView.as_view(), name="my-ideas"),
    path("my-ideas/<int:id>/", IdeaDetailView.as_view(), name="idea-detail"),
    path("idea-delete/<int:id>/", IdeaDeleteView.as_view(), name="idea-delete"),
    path(
        "update-report-steps/<int:id>/",
        UpdateReportStepsView.as_view(),
        name="update-report-steps",
    ),
    path(
        "generate-business-plan/<int:id>/",
        GenerateBusinessPlanView.as_view(),
        name="generate-business-plan",
    ),
    path("business-plans/", BusinessPlanListView.as_view(), name="business-plans"),
    path(
        "business-plan-detail/<int:id>/",
        BusinessPlanDetailView.as_view(),
        name="business-plan-detail",
    ),
    path(
        "business-plans/<int:id>/delete/",
        BusinessPlanSoftDeleteView.as_view(),
        name="business-plan-soft-delete",
    ),
]
