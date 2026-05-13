"""
AI-Powered Insights Engine
Provides anomaly detection, predictive analysis, and intelligent insights
"""

from datetime import datetime, timedelta
from typing import List, Dict
import statistics


class InsightsEngine:
    """Generates AI-powered insights from operational data"""
    
    def __init__(self):
        self.insights = []
        self.anomalies = []
        self.predictions = []
        
    def analyze_attendance_patterns(self, attendance_data: List[Dict]) -> List[Dict]:
        """Detect anomalies in attendance patterns"""
        anomalies = []
        
        if not attendance_data or len(attendance_data) < 5:
            return anomalies
            
        # Calculate average and std dev
        attendance_values = [d.get('attendance_percent', 0) for d in attendance_data]
        if not attendance_values:
            return anomalies
            
        avg_attendance = statistics.mean(attendance_values)
        std_dev = statistics.stdev(attendance_values) if len(attendance_values) > 1 else 0
        
        # Find outliers (>2 std devs from mean)
        for idx, data in enumerate(attendance_data):
            attendance = data.get('attendance_percent', 0)
            if abs(attendance - avg_attendance) > 2 * std_dev:
                anomalies.append({
                    "type": "attendance_anomaly",
                    "severity": "high" if attendance < avg_attendance - 2*std_dev else "medium",
                    "engineer": data.get('engineer_name', f"Engineer {idx}"),
                    "message": f"Attendance {attendance}% deviates significantly from average {avg_attendance:.1f}%",
                    "value": attendance,
                    "threshold": f"{avg_attendance - 2*std_dev:.1f}%",
                })
                
        return anomalies
        
    def detect_visit_spikes(self, visit_data: List[Dict]) -> List[Dict]:
        """Detect unusual spikes in visit volume"""
        anomalies = []
        
        if not visit_data or len(visit_data) < 7:
            return anomalies
            
        # Get last 7 days vs previous 7 days
        recent = sum(d.get('visits', 0) for d in visit_data[-7:]) / 7
        previous = sum(d.get('visits', 0) for d in visit_data[-14:-7]) / 7
        
        if previous > 0:
            change_percent = ((recent - previous) / previous) * 100
            if abs(change_percent) > 30:  # >30% change
                anomalies.append({
                    "type": "visit_spike",
                    "severity": "high" if change_percent > 50 else "medium",
                    "message": f"Visit volume changed by {change_percent:+.1f}% in last week",
                    "recent_avg": f"{recent:.0f}",
                    "previous_avg": f"{previous:.0f}",
                    "change_percent": f"{change_percent:+.1f}%",
                })
                
        return anomalies
        
    def identify_underperformers(self, engineer_data: List[Dict], threshold: float = 70.0) -> List[Dict]:
        """Identify underperforming engineers"""
        anomalies = []
        
        for engineer in engineer_data:
            completion_rate = engineer.get('completion_rate', 100)
            if completion_rate < threshold:
                anomalies.append({
                    "type": "underperformer",
                    "severity": "high" if completion_rate < threshold - 15 else "medium",
                    "engineer": engineer.get('engineer_name', 'Unknown'),
                    "message": f"Completion rate {completion_rate:.1f}% is below target {threshold:.1f}%",
                    "completion_rate": completion_rate,
                    "gap": f"{threshold - completion_rate:.1f}%",
                })
                
        return anomalies
        
    def detect_site_issues(self, site_data: List[Dict]) -> List[Dict]:
        """Detect sites with persistent issues"""
        anomalies = []
        
        for site in site_data:
            days_offline = site.get('days_offline', 0)
            if days_offline > 60:
                anomalies.append({
                    "type": "offline_duration",
                    "severity": "high" if days_offline > 90 else "medium",
                    "site_id": site.get('site_id', 'Unknown'),
                    "site_name": site.get('site_name', 'Unknown Site'),
                    "message": f"Site offline for {days_offline} days - exceeds normal threshold",
                    "days_offline": days_offline,
                    "recommendation": "Prioritize for maintenance/restoration",
                })
                
        return anomalies
        
    def predict_staffing_needs(self, visit_trends: List[Dict]) -> Dict:
        """Predict future staffing requirements"""
        prediction = {
            "type": "staffing_forecast",
            "period": "next_30_days",
            "current_staff": 20,
            "recommended_staff": 20,
            "basis": "historical visit patterns",
            "confidence": 0.75,
        }
        
        if visit_trends and len(visit_trends) > 7:
            # Analyze trend
            recent_visits = [d.get('visits', 0) for d in visit_trends[-7:]]
            avg_recent = statistics.mean(recent_visits)
            
            # Predict based on trend
            if avg_recent > 2500:  # High visit volume
                prediction["recommended_staff"] = 25
                prediction["action"] = "Consider additional resources for high-volume period"
            elif avg_recent < 1500:  # Low visit volume
                prediction["recommended_staff"] = 15
                prediction["action"] = "Can optimize staffing for lower-volume period"
                
        return prediction
        
    def generate_intelligent_insights(self, data: Dict) -> List[Dict]:
        """Generate comprehensive insights"""
        insights = []
        
        # Extract data
        metrics = data.get('metrics', {})
        trends = data.get('trends', [])
        engineers = data.get('engineers', [])
        sites = data.get('sites', [])
        
        # 1. Efficiency insight
        completion_rate = metrics.get('completion_rate', 0)
        if completion_rate > 90:
            insights.append({
                "category": "efficiency",
                "type": "positive",
                "severity": "low",
                "title": "High Completion Rate",
                "message": f"Field operations achieving {completion_rate}% completion rate - excellent performance",
                "recommendation": "Maintain current practices and share best practices across team",
            })
        elif completion_rate < 70:
            insights.append({
                "category": "efficiency",
                "type": "warning",
                "severity": "high",
                "title": "Low Completion Rate",
                "message": f"Completion rate at {completion_rate}% is below target (70% minimum)",
                "recommendation": "Review bottlenecks, provide additional training, or adjust visit scheduling",
            })
            
        # 2. Availability insight
        attendance = metrics.get('avg_attendance', 0)
        if attendance > 90:
            insights.append({
                "category": "availability",
                "type": "positive",
                "severity": "low",
                "title": "Strong Attendance",
                "message": f"Average attendance at {attendance}% indicates reliable workforce",
                "recommendation": "Continue to monitor and recognize top performers",
            })
            
        # 3. Infrastructure insight
        offline_sites = metrics.get('offline_sites', 0)
        if offline_sites > 1000:
            insights.append({
                "category": "infrastructure",
                "type": "alert",
                "severity": "high",
                "title": "High Offline Site Count",
                "message": f"{offline_sites} sites currently offline - significant infrastructure challenge",
                "recommendation": "Prioritize maintenance and restoration activities",
            })
            
        # 4. Trend insight
        if trends and len(trends) > 14:
            recent_avg = statistics.mean([t.get('visits', 0) for t in trends[-7:]])
            older_avg = statistics.mean([t.get('visits', 0) for t in trends[-14:-7]])
            if older_avg > 0:
                trend_change = ((recent_avg - older_avg) / older_avg) * 100
                if trend_change > 20:
                    insights.append({
                        "category": "trend",
                        "type": "positive",
                        "severity": "low",
                        "title": "Growing Visit Volume",
                        "message": f"Visit volume increased by {trend_change:.1f}% compared to previous week",
                        "recommendation": "Ensure adequate resources to handle growth",
                    })
                elif trend_change < -20:
                    insights.append({
                        "category": "trend",
                        "type": "warning",
                        "severity": "medium",
                        "title": "Declining Visit Volume",
                        "message": f"Visit volume declined by {abs(trend_change):.1f}% - investigate cause",
                        "recommendation": "Review scheduling, customer satisfaction, or market conditions",
                    })
                    
        return insights
        
    def score_health_metrics(self, data: Dict) -> Dict:
        """Generate health score (0-100)"""
        score = 50  # Base score
        metrics = data.get('metrics', {})
        
        # Scoring criteria (each worth up to 50 points divided among factors)
        completion_rate = metrics.get('completion_rate', 0)
        score += min(completion_rate * 0.5, 15)  # Up to 15 points
        
        attendance = metrics.get('avg_attendance', 0)
        score += min(attendance * 0.5, 15)  # Up to 15 points
        
        # Penalize high offline rate
        offline_sites = metrics.get('offline_sites', 0)
        if offline_sites > 2000:
            score -= 10
        elif offline_sites < 1000:
            score += 10
            
        # Cap score at 100
        return {
            "health_score": min(max(score, 0), 100),
            "rating": "Excellent" if score >= 80 else "Good" if score >= 60 else "Fair" if score >= 40 else "Poor",
            "breakdown": {
                "completion_impact": min(completion_rate * 0.5, 15),
                "attendance_impact": min(attendance * 0.5, 15),
                "infrastructure_impact": max(-10, min(10, (2000 - offline_sites) / 200)),
            }
        }
