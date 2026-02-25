import json

from django.conf import settings
from groq import Groq
from tavily import TavilyClient


class MarketAnalysisService:
    def __init__(self):
        self.tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)
        self.groq = Groq(api_key=settings.GROQ_API_KEY)

    def _extract_score(self, analysis_data):
        if isinstance(analysis_data, dict):
            score = analysis_data.get("score", 0)
            try:
                return min(max(int(score), 0), 100)
            except (ValueError, TypeError):
                return 0
        return 0

    def run_full_analysis(self, idea_title, idea_description):
        search_query = f"{idea_title} {idea_description} competitors market trends 2026"

        response = self.tavily.search(
            query=search_query, search_depth="advanced", max_results=5
        )

        if isinstance(response, dict):
            search_results = response.get("results", [])
        elif isinstance(response, list):
            search_results = response
        else:
            search_results = []

        context_list = []
        cleaned_results = []

        for res in search_results:
            if isinstance(res, dict):
                url = res.get("url", "N/A")
                content = res.get("content", "No content available")
                title = res.get("title", "No Title")

                context_list.append(f"Source: {url}\nContent: {content}")

                cleaned_results.append({"title": title, "url": url, "content": content})

        context = "\n".join(context_list)

        system_prompt = (
            "You are a senior startup consultant. "
            "You MUST respond ONLY with a valid JSON object. Do not add any introductory text or markdown formatting outside the JSON."
        )

        user_prompt = (
            f"Idea: {idea_title}\n"
            f"Description: {idea_description}\n"
            f"Market Data: {context}\n\n"
            f"Act as a strict Venture Capitalist consultant. Analyze the idea based on the market data provided.\n"
            f"CRITICAL INSTRUCTION: Calculate a dynamic and realistic viability score between 1 and 100 based on market gaps, threats, and execution difficulty. DO NOT use a default score. You MUST replace the placeholder string in 'score' with your actual calculated integer.\n\n"
            f"Provide your analysis STRICTLY in the following JSON structure:\n"
            f"{{\n"
            f'  "swot": {{\n'
            f'    "strengths": ["point 1", "point 2"],\n'
            f'    "weaknesses": ["point 1", "point 2"],\n'
            f'    "opportunities": ["point 1", "point 2"],\n'
            f'    "threats": ["point 1", "point 2"]\n'
            f"  }},\n"
            f'  "competitors": ["competitor 1", "competitor 2"],\n'
            f'  "market_gap": "Focus on untapped opportunities and white spaces in the market.",\n'
            f'  "score": "<REPLACE_WITH_CALCULATED_INTEGER_1_TO_100>",\n'
            f'  "steps": [\n'
            f'    {{ "id": 1, "task": "Specific action item 1", "status": "pending" }},\n'
            f'    {{ "id": 2, "task": "Specific action item 2", "status": "pending" }}\n'
            f"  ],\n"
            f'  "full_report_markdown": "# Investor-Ready Report\\n\\nDetailed analysis for PDF export..."\n'
            f"}}"
        )

        chat_completion = self.groq.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
        )

        try:
            analysis_data = json.loads(chat_completion.choices[0].message.content)
        except json.JSONDecodeError:
            analysis_data = {
                "swot": {},
                "score": 0,
                "full_report_markdown": "Error parsing AI response.",
            }

        extracted_score = self._extract_score(analysis_data)

        return {
            "raw_data": cleaned_results,
            "analysis": analysis_data,
            "score": extracted_score,
        }


class BusinessPlanService:
    def __init__(self):
        self.groq = Groq(api_key=settings.GROQ_API_KEY)

    def generate_business_plan(self, idea_title, idea_description, analysis_data):
        """
        Daha önce üretilen analizi kullanarak JSON formatında kapsamlı bir iş planı üretir.
        """
        swot = analysis_data.get("swot", {})
        gap = analysis_data.get("market_gap", "")

        system_prompt = (
            "You are an expert business strategist and startup mentor. "
            "You MUST respond ONLY with a valid JSON object. Do not include markdown blocks like ```json."
        )

        user_prompt = (
            f"Based on the following validated data, create a comprehensive 12-month Business Plan for: {idea_title}\n\n"
            f"Description: {idea_description}\n"
            f"SWOT Analysis: {json.dumps(swot)}\n"
            f"Market Gap: {gap}\n\n"
            f"Provide the output STRICTLY in the following JSON structure:\n"
            f"{{\n"
            f'  "executive_summary": "Detailed executive summary here...",\n'
            f'  "market_analysis": "Market Analysis and TAM/SAM/SOM breakdown...",\n'
            f'  "competitor_positioning": "How it compares to competitors...",\n'
            f'  "target_audience": "Target Audience & Personas...",\n'
            f'  "revenue_model": "Revenue Model & Pricing Strategy...",\n'
            f'  "marketing_strategy": "Marketing & Acquisition Channels...",\n'
            f'  "tech_architecture": "Technical Architecture Overview...",\n'
            f'  "roadmap": [\n'
            f'    {{ "month": "Month 1-3", "focus": "MVP Development" }},\n'
            f'    {{ "month": "Month 4-6", "focus": "Beta Launch" }}\n'
            f"  ]\n"
            f"}}"
        )

        chat_completion = self.groq.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
        )

        try:
            plan_data = json.loads(chat_completion.choices[0].message.content)
            return plan_data
        except json.JSONDecodeError:
            return None
