from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from ideas.models import AnalysisReport, BusinessIdea, BusinessPlan


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_user(api_client, django_user_model):
    """Test için giriş yapmış bir kullanıcı sağlar."""
    user = django_user_model.objects.create_user(
        username="idea_owner", password="password123"
    )
    api_client.force_authenticate(user=user)
    return user


@pytest.mark.django_db
class TestIdeaAnalysis:
    url = reverse("idea-analysis")

    @patch("ideas.views.MarketAnalysisService.run_full_analysis")
    def test_analyze_create_success(
        self, mock_run_analysis, api_client, authenticated_user
    ):
        """Başarılı bir fikir oluşturma ve AI analizi testi."""

        mock_run_analysis.return_value = {
            "raw_data": [
                {"title": "Competitor 1", "url": "http://test.com", "content": "data"}
            ],
            "analysis": {
                "swot": {"strengths": ["test"], "weaknesses": []},
                "score": 85,
                "steps": [{"id": 1, "task": "Do research", "status": "pending"}],
            },
            "score": 85,
        }

        payload = {
            "title": "AI Coffee Roaster",
            "description": "Smart coffee roasting machine with mobile app control.",
        }

        response = api_client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == payload["title"]

        idea = BusinessIdea.objects.get(title=payload["title"])
        assert idea.user == authenticated_user

        report = AnalysisReport.objects.get(idea=idea)
        assert report.score == 85
        assert len(report.steps) == 1
        assert report.steps[0]["task"] == "Do research"

    @patch("ideas.views.MarketAnalysisService.run_full_analysis")
    def test_analyze_create_ai_error(
        self, mock_run_analysis, api_client, authenticated_user
    ):
        """AI servisi hata verirse 500 dönmeli."""

        mock_run_analysis.side_effect = Exception("API Connection Failed")

        payload = {"title": "Broken Idea", "description": "Test for error handling"}

        response = api_client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "AI Analysis Error" in response.data["message"]

    def test_analyze_create_invalid_data(self, api_client, authenticated_user):
        """Eksik veri gönderildiğinde 400 dönmeli."""

        payload = {"title": ""}
        response = api_client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "description" in response.data


#############IDEAS LIST TEST##################
@pytest.mark.django_db
class TestMyIdeasListView:
    url = reverse("my-ideas")

    @pytest.fixture
    def setup_ideas(self, authenticated_user):
        """Test için farklı skorlarda ve isimlerde fikirler oluşturur."""
        idea1 = BusinessIdea.objects.create(
            user=authenticated_user, title="Alpha Project", description="Desc 1"
        )
        AnalysisReport.objects.create(idea=idea1, score=50)
        AnalysisReport.objects.create(idea=idea1, score=90)

        idea2 = BusinessIdea.objects.create(
            user=authenticated_user, title="Beta App", description="Desc 2"
        )
        AnalysisReport.objects.create(idea=idea2, score=70)

        return idea1, idea2

    def test_list_ideas_success(self, api_client, authenticated_user, setup_ideas):
        """Kullanıcının kendi fikirlerini listeleyebildiğini ve skorun doğru geldiğini doğrular."""
        response = api_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2

        assert response.data["results"][0]["score"] == 70
        assert response.data["results"][1]["score"] == 90

    def test_list_ideas_search_filter(
        self, api_client, authenticated_user, setup_ideas
    ):
        """'search' parametresinin başlığa göre filtreleme yaptığını doğrular."""
        response = api_client.get(self.url, {"search": "Alpha"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["title"] == "Alpha Project"

    def test_list_ideas_ordering_score(
        self, api_client, authenticated_user, setup_ideas
    ):
        """Skora göre sıralamanın (küçükten büyüğe) çalıştığını doğrular."""
        response = api_client.get(self.url, {"ordering": "score"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"][0]["title"] == "Beta App"

    def test_list_ideas_ordering_score_desc(
        self, api_client, authenticated_user, setup_ideas
    ):
        """Skora göre tersten sıralamanın (-score) çalıştığını doğrular."""
        response = api_client.get(self.url, {"ordering": "-score"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"][0]["title"] == "Alpha Project"

    def test_list_ideas_unauthenticated_fails(self, api_client):
        """Giriş yapmamış kullanıcı listeye erişememeli."""
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


#### IDEA DETAIL TEST###
@pytest.mark.django_db
class TestIdeaDetailView:

    def test_get_idea_detail_success(self, api_client, authenticated_user):
        idea = BusinessIdea.objects.create(
            user=authenticated_user,
            title="Detail Test Project",
            description="Testing details",
        )
        AnalysisReport.objects.create(
            idea=idea, score=88, ai_analysis={"summary": "Good idea"}
        )

        url = reverse("idea-detail", kwargs={"id": idea.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Detail Test Project"
        assert len(response.data["reports"]) == 1
        assert response.data["reports"][0]["score"] == 88

    def test_get_other_user_idea_fails(
        self, api_client, authenticated_user, django_user_model
    ):
        other_user = django_user_model.objects.create_user(
            username="other", password="password123"
        )
        other_idea = BusinessIdea.objects.create(
            user=other_user, title="Secret Project"
        )

        url = reverse("idea-detail", kwargs={"id": other_idea.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_deleted_idea_fails(self, api_client, authenticated_user):
        deleted_idea = BusinessIdea.objects.create(
            user=authenticated_user, title="Deleted Project", is_deleted=True
        )

        url = reverse("idea-detail", kwargs={"id": deleted_idea.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


#### IDEA DELETE TEST###
@pytest.mark.django_db
class TestIdeaDeleteView:

    def test_delete_idea_success(self, api_client, authenticated_user):
        idea = BusinessIdea.objects.create(
            user=authenticated_user, title="Delete Me", description="To be deleted"
        )
        url = reverse("idea-delete", kwargs={"id": idea.id})

        response = api_client.patch(url)

        assert response.status_code == status.HTTP_200_OK
        assert (
            response.data["message"]
            == "Idea and related plan connections are deleted successfully."
        )

        idea.refresh_from_db()
        assert idea.is_deleted is True

    def test_delete_other_user_idea_fails(
        self, api_client, authenticated_user, django_user_model
    ):
        other_user = django_user_model.objects.create_user(
            username="otheruser", password="password123"
        )
        other_idea = BusinessIdea.objects.create(user=other_user, title="Other's Idea")
        url = reverse("idea-delete", kwargs={"id": other_idea.id})

        response = api_client.patch(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

        other_idea.refresh_from_db()
        assert other_idea.is_deleted is False

    def test_delete_already_deleted_idea_fails(self, api_client, authenticated_user):
        idea = BusinessIdea.objects.create(
            user=authenticated_user, title="Already Deleted", is_deleted=True
        )
        url = reverse("idea-delete", kwargs={"id": idea.id})

        response = api_client.patch(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


#### UPDATE STEPS TEST ###
@pytest.mark.django_db
class TestUpdateReportStepsView:

    def test_update_steps_success(self, api_client, authenticated_user):
        idea = BusinessIdea.objects.create(
            user=authenticated_user,
            title="Steps Test",
            description="Testing steps update",
        )
        report = AnalysisReport.objects.create(
            idea=idea, steps=[{"id": 1, "task": "Old Task", "status": "pending"}]
        )
        url = reverse("update-report-steps", kwargs={"id": report.id})
        new_steps = [{"id": 1, "task": "Old Task", "status": "completed"}]

        response = api_client.patch(url, {"steps": new_steps}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["message"] == "success"
        assert response.data["data"] == new_steps

        report.refresh_from_db()
        assert report.steps == new_steps

    def test_update_steps_no_data_fails(self, api_client, authenticated_user):
        idea = BusinessIdea.objects.create(
            user=authenticated_user, title="No Data Test"
        )
        report = AnalysisReport.objects.create(idea=idea, steps=[])
        url = reverse("update-report-steps", kwargs={"id": report.id})

        response = api_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "No steps data provided"

    def test_update_other_user_report_steps_fails(
        self, api_client, authenticated_user, django_user_model
    ):
        other_user = django_user_model.objects.create_user(
            username="other", password="password123"
        )
        other_idea = BusinessIdea.objects.create(user=other_user, title="Other Idea")
        other_report = AnalysisReport.objects.create(idea=other_idea, steps=[])
        url = reverse("update-report-steps", kwargs={"id": other_report.id})

        response = api_client.patch(url, {"steps": []}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["message"] == "Not found"


##### GENERATE BUSINESS PLAN TEST ###
@pytest.mark.django_db
class TestGenerateBusinessPlanView:

    @patch("ideas.views.BusinessPlanService.generate_business_plan")
    def test_generate_business_plan_success(
        self, mock_generate, api_client, authenticated_user
    ):
        idea = BusinessIdea.objects.create(
            user=authenticated_user,
            title="SaaS Platform",
            description="AI powered management tool",
        )
        report = AnalysisReport.objects.create(
            idea=idea,
            ai_analysis={
                "swot": {"strengths": ["Fast"]},
                "market_gap": "Unserved small businesses",
            },
            score=80,
        )

        mock_generate.return_value = {
            "executive_summary": "Great business summary",
            "market_analysis": "Big market",
            "competitor_positioning": "Leader",
            "target_audience": "SMEs",
            "revenue_model": "Subscription",
            "marketing_strategy": "Ads",
            "tech_architecture": "Django & Next.js",
            "roadmap": [{"month": "Month 1-3", "focus": "MVP"}],
        }

        url = reverse("generate-business-plan", kwargs={"id": report.id})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["message"] == "İş planı başarıyla oluşturuldu."
        assert "business_plan_id" in response.data

        plan = BusinessPlan.objects.get(id=response.data["business_plan_id"])
        assert plan.report == report
        assert plan.executive_summary == "Great business summary"
        assert plan.revenue_model == "Subscription"

    @patch("ideas.views.BusinessPlanService.generate_business_plan")
    def test_generate_business_plan_ai_error(
        self, mock_generate, api_client, authenticated_user
    ):
        idea = BusinessIdea.objects.create(
            user=authenticated_user, title="Failure Test"
        )
        report = AnalysisReport.objects.create(idea=idea, ai_analysis={}, score=50)

        mock_generate.return_value = None

        url = reverse("generate-business-plan", kwargs={"id": report.id})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert (
            response.data["error"]
            == "Yapay zeka iş planı oluştururken bir hata oluştu."
        )

    def test_generate_business_plan_not_found(self, api_client, authenticated_user):
        url = reverse("generate-business-plan", kwargs={"id": 9999})
        response = api_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"] == "Rapor bulunamadı."


###### BUSINESS PLAN LIST TEST ######
@pytest.mark.django_db
class TestBusinessPlanListView:
    url = reverse("business-plans")

    @pytest.fixture
    def setup_plans(self, authenticated_user):
        idea1 = BusinessIdea.objects.create(user=authenticated_user, title="Alpha Tech")
        report1 = AnalysisReport.objects.create(idea=idea1)
        plan1 = BusinessPlan.objects.create(report=report1)

        idea2 = BusinessIdea.objects.create(user=authenticated_user, title="Beta Food")
        report2 = AnalysisReport.objects.create(idea=idea2)
        plan2 = BusinessPlan.objects.create(report=report2)

        return plan1, plan2

    def test_list_business_plans_success(
        self, api_client, authenticated_user, setup_plans
    ):
        response = api_client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 2
        assert "title" in response.data["results"][0]
        assert "idea_id" in response.data["results"][0]

    def test_list_business_plans_search_filter(
        self, api_client, authenticated_user, setup_plans
    ):
        response = api_client.get(self.url, {"search": "Alpha"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["title"] == "Alpha Tech"

    def test_list_business_plans_ordering(
        self, api_client, authenticated_user, setup_plans
    ):
        response = api_client.get(self.url, {"ordering": "created_at"})
        assert response.data["results"][0]["title"] == "Alpha Tech"

        response = api_client.get(self.url, {"ordering": "-created_at"})
        assert response.data["results"][0]["title"] == "Beta Food"

    def test_list_business_plans_is_deleted_filter(
        self, api_client, authenticated_user
    ):
        idea = BusinessIdea.objects.create(user=authenticated_user, title="Visible")
        report = AnalysisReport.objects.create(idea=idea)

        BusinessPlan.objects.create(report=report, is_deleted=True)

        deleted_idea = BusinessIdea.objects.create(
            user=authenticated_user, title="Deleted", is_deleted=True
        )
        deleted_report = AnalysisReport.objects.create(idea=deleted_idea)
        BusinessPlan.objects.create(report=deleted_report, is_deleted=False)

        response = api_client.get(self.url)
        assert len(response.data["results"]) == 0

    def test_list_business_plans_unauthenticated_fails(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


####### BUSINESS PLAN DETAIL TEST ###########
@pytest.mark.django_db
class TestBusinessPlanDetailView:

    def test_get_business_plan_detail_success(self, api_client, authenticated_user):
        idea = BusinessIdea.objects.create(
            user=authenticated_user,
            title="Detail Plan Project",
            description="Detail Desc",
        )
        report = AnalysisReport.objects.create(idea=idea)
        plan = BusinessPlan.objects.create(
            report=report,
            executive_summary="Summary text",
            revenue_model="SaaS",
            roadmap=[{"month": "1", "focus": "Launch"}],
        )

        url = reverse("business-plan-detail", kwargs={"id": plan.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Detail Plan Project"
        assert response.data["executive_summary"] == "Summary text"
        assert response.data["revenue_model"] == "SaaS"
        assert response.data["roadmap"][0]["focus"] == "Launch"

    def test_get_other_user_business_plan_fails(
        self, api_client, authenticated_user, django_user_model
    ):
        other_user = django_user_model.objects.create_user(
            username="otherowner", password="password123"
        )
        other_idea = BusinessIdea.objects.create(user=other_user, title="Other Plan")
        other_report = AnalysisReport.objects.create(idea=other_idea)
        other_plan = BusinessPlan.objects.create(report=other_report)

        url = reverse("business-plan-detail", kwargs={"id": other_plan.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_business_plan_with_deleted_idea_fails(
        self, api_client, authenticated_user
    ):
        deleted_idea = BusinessIdea.objects.create(
            user=authenticated_user, title="Deleted Idea", is_deleted=True
        )
        report = AnalysisReport.objects.create(idea=deleted_idea)
        plan = BusinessPlan.objects.create(report=report)

        url = reverse("business-plan-detail", kwargs={"id": plan.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_soft_deleted_business_plan_fails(self, api_client, authenticated_user):
        idea = BusinessIdea.objects.create(user=authenticated_user, title="Active Idea")
        report = AnalysisReport.objects.create(idea=idea)
        deleted_plan = BusinessPlan.objects.create(report=report, is_deleted=True)

        url = reverse("business-plan-detail", kwargs={"id": deleted_plan.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


##########BUSINESS PLAN DELETE TEST##########
@pytest.mark.django_db
class TestBusinessPlanSoftDeleteView:

    def test_soft_delete_business_plan_success(self, api_client, authenticated_user):
        idea = BusinessIdea.objects.create(
            user=authenticated_user, title="Delete Plan Test"
        )
        report = AnalysisReport.objects.create(idea=idea)
        plan = BusinessPlan.objects.create(report=report, is_deleted=False)

        url = reverse("business-plan-soft-delete", kwargs={"id": plan.id})
        response = api_client.patch(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "Business plan successfully deleted."

        plan.refresh_from_db()
        assert plan.is_deleted is True
        assert plan.report is None

    def test_delete_other_user_business_plan_fails(
        self, api_client, authenticated_user, django_user_model
    ):
        other_user = django_user_model.objects.create_user(
            username="stranger", password="password123"
        )
        other_idea = BusinessIdea.objects.create(user=other_user, title="Other's Plan")
        other_report = AnalysisReport.objects.create(idea=other_idea)
        other_plan = BusinessPlan.objects.create(report=other_report, is_deleted=False)

        url = reverse("business-plan-soft-delete", kwargs={"id": other_plan.id})
        response = api_client.patch(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

        other_plan.refresh_from_db()
        assert other_plan.is_deleted is False
        assert other_plan.report is not None

    def test_delete_already_deleted_business_plan_fails(
        self, api_client, authenticated_user
    ):
        idea = BusinessIdea.objects.create(
            user=authenticated_user, title="Already Gone"
        )
        report = AnalysisReport.objects.create(idea=idea)
        plan = BusinessPlan.objects.create(report=report, is_deleted=True)

        url = reverse("business-plan-soft-delete", kwargs={"id": plan.id})
        response = api_client.patch(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
