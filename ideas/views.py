from django.db.models import OuterRef, Subquery
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ideas.models import AnalysisReport, BusinessIdea, BusinessPlan
from ideas.paginations import Pagination10
from ideas.serializers import (BusinessIdeaListSerializer,
                               BusinessIdeaSerializer,
                               BusinessPlanDetailSerializer,
                               BusinessPlanListSerializer)
from ideas.services import BusinessPlanService, MarketAnalysisService

# ideas/views.py


class IdeaAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BusinessIdeaSerializer(data=request.data)
        if serializer.is_valid():
            idea = serializer.save(user=request.user)

            service = MarketAnalysisService()
            try:
                analysis_results = service.run_full_analysis(
                    idea.title, idea.description
                )

                AnalysisReport.objects.create(
                    idea=idea,
                    raw_search_data=analysis_results["raw_data"],
                    ai_analysis=analysis_results["analysis"],
                    score=analysis_results["score"],
                    steps=analysis_results["analysis"].get("steps", []),
                )

                return Response(
                    BusinessIdeaSerializer(idea).data, status=status.HTTP_201_CREATED
                )
            except Exception as e:
                return Response(
                    {"message": f"AI Analysis Error: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyIdeasListView(ListAPIView):
    serializer_class = BusinessIdeaListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination10

    def get_queryset(self):
        score_subquery = (
            AnalysisReport.objects.filter(idea=OuterRef("pk"))
            .order_by("-created_at")
            .values("score")[:1]
        )

        queryset = BusinessIdea.objects.filter(
            user=self.request.user, is_deleted=False
        ).annotate(annotated_score=Subquery(score_subquery))

        order_param = self.request.query_params.get("ordering")

        title_query = self.request.query_params.get("search")
        if title_query:
            queryset = queryset.filter(title__icontains=title_query)

        if order_param == "score":
            queryset = queryset.order_by("annotated_score")
        elif order_param == "-score":
            queryset = queryset.order_by("-annotated_score")
        elif order_param == "created_at":
            queryset = queryset.order_by("created_at")
        elif order_param == "-created_at":
            queryset = queryset.order_by("-created_at")
        else:
            queryset = queryset.order_by("-created_at")

        return queryset


class IdeaDetailView(RetrieveAPIView):
    serializer_class = BusinessIdeaSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return BusinessIdea.objects.filter(
            user=self.request.user, is_deleted=False
        ).prefetch_related("reports")


class IdeaDeleteView(UpdateAPIView):
    serializer_class = BusinessIdeaSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return BusinessIdea.objects.filter(user=self.request.user, is_deleted=False)

    def patch(self, request, *args, **kwargs):
        target_idea = self.get_object()

        target_idea.is_deleted = True
        target_idea.save(update_fields=["is_deleted"])

        BusinessPlan.objects.filter(report__idea=target_idea).update(report=None)

        return Response(
            {"message": "Idea and related plan connections are deleted successfully."},
            status=status.HTTP_200_OK,
        )


class UpdateReportStepsView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):
        try:
            report = AnalysisReport.objects.get(id=id, idea__user=request.user)
            steps_data = request.data.get("steps")

            if steps_data is not None:
                report.steps = steps_data
                report.save(update_fields=["steps"])
                return Response({"message": "success", "data": report.steps})

            return Response({"message": "No steps data provided"}, status=400)
        except AnalysisReport.DoesNotExist:
            return Response({"message": "Not found"}, status=404)


class GenerateBusinessPlanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            report = AnalysisReport.objects.select_related("idea").get(
                id=id, idea__user=request.user
            )

            service = BusinessPlanService()
            plan_data = service.generate_business_plan(
                report.idea.title, report.idea.description, report.ai_analysis
            )

            if not plan_data:
                return Response(
                    {"error": "Yapay zeka iş planı oluştururken bir hata oluştu."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            business_plan = BusinessPlan.objects.create(
                report=report,
                executive_summary=plan_data.get("executive_summary", ""),
                market_analysis=plan_data.get("market_analysis", ""),
                competitor_positioning=plan_data.get("competitor_positioning", ""),
                target_audience=plan_data.get("target_audience", ""),
                revenue_model=plan_data.get("revenue_model", ""),
                marketing_strategy=plan_data.get("marketing_strategy", ""),
                tech_architecture=plan_data.get("tech_architecture", ""),
                roadmap=plan_data.get("roadmap", []),
                is_deleted=False,
            )

            return Response(
                {
                    "message": "İş planı başarıyla oluşturuldu.",
                    "business_plan_id": business_plan.id,
                },
                status=status.HTTP_201_CREATED,
            )

        except AnalysisReport.DoesNotExist:
            return Response(
                {"error": "Rapor bulunamadı."}, status=status.HTTP_404_NOT_FOUND
            )


class BusinessPlanListView(ListAPIView):
    serializer_class = BusinessPlanListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = Pagination10

    def get_queryset(self):
        queryset = BusinessPlan.objects.filter(
            report__idea__user=self.request.user,
            report__idea__is_deleted=False,
            is_deleted=False,
        ).select_related("report", "report__idea")

        title_query = self.request.query_params.get("search")
        if title_query:
            queryset = queryset.filter(report__idea__title__icontains=title_query)

        order_param = self.request.query_params.get("ordering")
        if order_param == "created_at":
            queryset = queryset.order_by("created_at")
        elif order_param == "-created_at":
            queryset = queryset.order_by("-created_at")
        else:
            queryset = queryset.order_by("-created_at")

        return queryset


class BusinessPlanDetailView(RetrieveAPIView):
    serializer_class = BusinessPlanDetailSerializer
    permission_classes = [IsAuthenticated]

    lookup_field = "id"

    def get_queryset(self):
        base_queryset = BusinessPlan.objects.filter(
            report__idea__user=self.request.user,
            report__idea__is_deleted=False,
            is_deleted=False,
        ).select_related("report", "report__idea")

        return base_queryset.filter(id=self.kwargs["id"])


class BusinessPlanSoftDeleteView(UpdateAPIView):
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return BusinessPlan.objects.filter(
            report__idea__user=self.request.user, is_deleted=False
        )

    def patch(self, request, *args, **kwargs):
        business_plan = self.get_object()

        business_plan.is_deleted = True
        business_plan.report = None
        business_plan.save(update_fields=["is_deleted", "report"])

        return Response(
            {"detail": "Business plan successfully deleted."}, status=status.HTTP_200_OK
        )
