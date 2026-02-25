from django.db import models

from users.models import Users


class BusinessIdea(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="ideas")
    title = models.CharField(max_length=255)
    description = models.TextField()
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class AnalysisReport(models.Model):
    idea = models.ForeignKey(
        BusinessIdea, on_delete=models.CASCADE, related_name="reports"
    )
    raw_search_data = models.JSONField(null=True, blank=True)
    ai_analysis = models.JSONField(null=True, blank=True)
    score = models.IntegerField(default=0)
    steps = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report for {self.idea.title}"


class BusinessPlan(models.Model):
    report = models.OneToOneField(
        "AnalysisReport",
        on_delete=models.CASCADE,
        related_name="business_plan_document",
        null=True,
        blank=True,
    )

    executive_summary = models.TextField(null=True, blank=True)
    market_analysis = models.TextField(null=True, blank=True)
    competitor_positioning = models.TextField(null=True, blank=True)
    target_audience = models.TextField(null=True, blank=True)
    revenue_model = models.TextField(null=True, blank=True)
    marketing_strategy = models.TextField(null=True, blank=True)
    tech_architecture = models.TextField(null=True, blank=True)

    roadmap = models.JSONField(default=list, blank=True)

    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Business Plan for {self.report.idea.title}"
