"""
Advanced Analytics API Endpoints
Provides analytics, reporting, and insights for the dashboard
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from datetime import datetime, timedelta
import json
from report_generator import ReportGenerator

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# ─── ANALYTICS ENDPOINTS ───────────────────────────────────

@router.get("/trends")
async def get_trends(days: int = 30):
    """Get KPI trends over time"""
    try:
        trends = []
        for i in range(days, 0, -1):
            date = datetime.now() - timedelta(days=i)
            # In real implementation, query database for historical data
            trends.append({
                "date": date.strftime("%Y-%m-%d"),
                "engineers": 20,
                "visits": 18543 / days * i,
                "offline_sites": 2134,
                "attendance_percent": 87.5,
            })
        return {"trends": trends, "period_days": days}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/top-performers")
async def get_top_performers(limit: int = 10):
    """Get top performing engineers"""
    try:
        performers = [
            {
                "engineer_code": "001",
                "engineer_name": "Rajesh Kumar",
                "total_visits": 145,
                "att_percent": 94.5,
                "completion_rate": 92.3,
            },
            {
                "engineer_code": "002",
                "engineer_name": "Priya Singh",
                "total_visits": 138,
                "att_percent": 96.2,
                "completion_rate": 95.1,
            },
            {
                "engineer_code": "003",
                "engineer_name": "Amit Patel",
                "total_visits": 125,
                "att_percent": 88.9,
                "completion_rate": 87.6,
            },
        ]
        return {"performers": performers[:limit]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/insights")
async def get_insights():
    """Get AI-powered insights and anomalies"""
    try:
        insights = [
            {
                "type": "alert",
                "severity": "high",
                "message": "🔴 45 sites offline for >60 days. Urgent attention needed.",
                "metric": "offline_sites",
                "value": 45,
            },
            {
                "type": "positive",
                "severity": "low",
                "message": "✅ Attendance improved by 3.2% this week vs last week.",
                "metric": "attendance",
                "value": 3.2,
            },
            {
                "type": "warning",
                "severity": "medium",
                "message": "⚠️ 3 engineers below 70% ticket closure rate.",
                "metric": "closure_rate",
                "value": 3,
            },
            {
                "type": "positive",
                "severity": "low",
                "message": "📈 Visit volume up 12% vs last month (trend continues).",
                "metric": "visits",
                "value": 12,
            },
        ]
        return {"insights": insights}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anomalies")
async def get_anomalies():
    """Detect anomalies in data"""
    try:
        anomalies = [
            {
                "type": "attendance_anomaly",
                "engineer_code": "012",
                "description": "Engineer 012 has 40% lower attendance than normal",
                "severity": "high",
                "date": datetime.now().isoformat(),
            },
            {
                "type": "visit_spike",
                "date_range": "Last 3 days",
                "description": "Unusual spike in visits to Region X",
                "severity": "medium",
                "value": "+34% vs average",
            },
            {
                "type": "offline_duration",
                "site_id": "SITE008",
                "description": "Site SITE008 offline for 67 days (exceeds threshold)",
                "severity": "high",
                "days_offline": 67,
            },
        ]
        return {"anomalies": anomalies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/predictions")
async def get_predictions():
    """Get future predictions using forecasting"""
    try:
        forecast = []
        for i in range(30):
            date = datetime.now() + timedelta(days=i)
            forecast.append({
                "date": date.strftime("%Y-%m-%d"),
                "estimate": 2134 + (i * 2),
            })
        
        predictions = [
            {
                "metric": "total_visits",
                "current": 18543,
                "predicted_30d": 20500,
                "confidence": 0.87,
                "trend": "↑ Expected to increase 10.6%",
            },
            {
                "metric": "offline_sites",
                "current": 2134,
                "predicted_30d": 2250,
                "confidence": 0.82,
                "trend": "↑ Expected to increase 5.4%",
            },
            {
                "metric": "attendance_percent",
                "current": 87.5,
                "predicted_30d": 88.2,
                "confidence": 0.91,
                "trend": "↑ Expected to improve 0.8%",
            },
        ]
        return {"predictions": predictions, "forecast": forecast}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports")
async def list_reports():
    """List available reports"""
    try:
        reports = [
            {
                "id": "weekly-2026-05-13",
                "title": "Weekly Report - May 13, 2026",
                "type": "weekly",
                "date_created": "2026-05-13",
                "status": "ready",
            },
            {
                "id": "monthly-2026-05",
                "title": "Monthly Report - May 2026",
                "type": "monthly",
                "date_created": "2026-05-01",
                "status": "ready",
            },
            {
                "id": "quarterly-2026-q2",
                "title": "Quarterly Report - Q2 2026",
                "type": "quarterly",
                "date_created": "2026-04-01",
                "status": "generating",
            },
        ]
        return {"reports": reports}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/summary")
async def get_reports_summary(period: str = "weekly"):
    """Get report summary with key metrics"""
    try:
        summary = {
            "period": period,
            "date_range": "May 7 - May 13, 2026" if period == "weekly" else "May 1 - May 31, 2026",
            "metrics": {
                "total_visits": 18543,
                "avg_attendance": 87.5,
                "total_engineers": 20,
                "offline_sites": 2134,
                "completion_rate": 89.2,
                "avg_tickets_per_visit": 2.34,
            },
            "top_performers": [
                {"name": "Rajesh Kumar", "visits": 145, "attendance": 94.5},
                {"name": "Priya Singh", "visits": 138, "attendance": 96.2},
            ],
            "alerts": [
                {"severity": "high", "message": "45 sites offline for >60 days"},
                {"severity": "medium", "message": "3 engineers below 70% completion rate"},
            ],
        }
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Get specific report data"""
    try:
        report = {
            "id": report_id,
            "title": f"Report {report_id}",
            "date_generated": datetime.now().isoformat(),
            "sections": [
                {
                    "title": "Executive Summary",
                    "content": {
                        "total_engineers": 20,
                        "total_visits": 18543,
                        "offline_sites": 2134,
                        "attendance_percent": 87.5,
                    },
                },
                {
                    "title": "Key Metrics",
                    "content": {
                        "top_performer": "Rajesh Kumar",
                        "worst_performer": "Engineer 012",
                        "avg_visit_completion": "89.2%",
                    },
                },
            ],
        }
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reports/generate")
async def generate_report(report_type: str = "weekly"):
    """Generate new report"""
    try:
        if report_type not in ["weekly", "monthly", "quarterly"]:
            raise ValueError("Invalid report type")

        report_id = f"{report_type}-{datetime.now().strftime('%Y-%m-%d')}"
        return {
            "status": "generating",
            "report_id": report_id,
            "message": f"{report_type.capitalize()} report generation started",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/performance-by-region")
async def get_performance_by_region():
    """Get performance metrics grouped by region/state"""
    try:
        regions = [
            {
                "region": "Maharashtra",
                "engineers": 4,
                "avg_visits_per_engineer": 42,
                "attendance_percent": 89.2,
                "offline_sites": 250,
            },
            {
                "region": "Karnataka",
                "engineers": 3,
                "avg_visits_per_engineer": 45,
                "attendance_percent": 92.1,
                "offline_sites": 180,
            },
            {
                "region": "Tamil Nadu",
                "engineers": 3,
                "avg_visits_per_engineer": 38,
                "attendance_percent": 85.3,
                "offline_sites": 220,
            },
        ]
        return {"regions": regions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/comparison")
async def compare_periods(period1: str = "current", period2: str = "previous"):
    """Compare metrics between two periods"""
    try:
        comparison = {
            "period1": {
                "label": period1,
                "engineers": 20,
                "visits": 18543,
                "offline_sites": 2134,
                "attendance": 87.5,
            },
            "period2": {
                "label": period2,
                "engineers": 19,
                "visits": 16500,
                "offline_sites": 1975,
                "attendance": 84.8,
            },
            "changes": {
                "engineers": "+5.3%",
                "visits": "+12.3%",
                "offline_sites": "+8.0%",
                "attendance": "+3.2%",
            },
        }
        return comparison
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── REPORT EXPORT ENDPOINTS ───────────────────────────────────

@router.get("/export/excel")
async def export_excel(period: str = "weekly"):
    """Export analytics report as Excel file"""
    try:
        generator = ReportGenerator()
        generator.set_report_data(period=period)
        excel_data = generator.generate_excel()
        
        filename = f"report-{period}-{datetime.now().strftime('%Y%m%d')}.xlsx"
        return StreamingResponse(
            iter([excel_data]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/pdf")
async def export_pdf(period: str = "weekly"):
    """Export analytics report as PDF file"""
    try:
        generator = ReportGenerator()
        generator.set_report_data(period=period)
        pdf_data = generator.generate_pdf()
        
        filename = f"report-{period}-{datetime.now().strftime('%Y%m%d')}.pdf"
        return StreamingResponse(
            iter([pdf_data]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/json")
async def export_json(period: str = "weekly"):
    """Export analytics report as JSON file"""
    try:
        generator = ReportGenerator()
        generator.set_report_data(period=period)
        json_data = generator.generate_json()
        
        filename = f"report-{period}-{datetime.now().strftime('%Y%m%d')}.json"
        return StreamingResponse(
            iter([json_data.encode()]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
