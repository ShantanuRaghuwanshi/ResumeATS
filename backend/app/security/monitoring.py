"""
Security monitoring and threat detection system
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from enum import Enum
import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass
import hashlib

from .audit_logging import (
    audit_logger,
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    log_security_event,
)


class ThreatLevel(Enum):
    """Threat severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AttackType(Enum):
    """Types of detected attacks"""

    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS_ATTEMPT = "xss_attempt"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    PROMPT_INJECTION = "prompt_injection"
    RATE_LIMIT_ABUSE = "rate_limit_abuse"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    DATA_EXFILTRATION = "data_exfiltration"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


@dataclass
class SecurityAlert:
    """Security alert data structure"""

    id: str
    timestamp: datetime
    threat_level: ThreatLevel
    attack_type: AttackType
    source_ip: str
    user_agent: str
    description: str
    details: Dict[str, Any]
    affected_resource: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    mitigation_applied: bool = False
    false_positive: bool = False


class SecurityMonitor:
    """Real-time security monitoring system"""

    def __init__(self):
        self.alerts: List[SecurityAlert] = []
        self.ip_activity: Dict[str, List[datetime]] = defaultdict(list)
        self.failed_attempts: Dict[str, int] = defaultdict(int)
        self.suspicious_patterns: Dict[str, int] = defaultdict(int)
        self.blocked_ips: Set[str] = set()
        self.monitoring_active = True

        # Pattern detection
        self.attack_patterns = {
            AttackType.SQL_INJECTION: [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
                r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
                r"(--|#|/\*|\*/)",
                r"(\bxp_cmdshell\b)",
            ],
            AttackType.XSS_ATTEMPT: [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"vbscript:",
                r"onload\s*=",
                r"onerror\s*=",
            ],
            AttackType.PATH_TRAVERSAL: [
                r"\.\./",
                r"\.\.\\",
                r"/etc/passwd",
                r"/proc/",
                r"C:\\Windows",
            ],
            AttackType.COMMAND_INJECTION: [
                r"[;&|`$(){}[\]<>]",
                r"\b(cat|ls|dir|type|copy|move|del|rm)\b",
                r"\b(wget|curl|nc|netcat|telnet|ssh)\b",
            ],
            AttackType.PROMPT_INJECTION: [
                r"ignore\s+previous\s+instructions",
                r"forget\s+everything",
                r"system\s*:",
                r"jailbreak",
                r"roleplay\s+as",
            ],
        }

        # Suspicious user agents
        self.suspicious_user_agents = [
            r"sqlmap",
            r"nikto",
            r"nmap",
            r"burp",
            r"owasp",
            r"scanner",
            r"bot.*attack",
            r"hack.*tool",
        ]

    async def analyze_request(
        self,
        ip_address: str,
        user_agent: str,
        endpoint: str,
        method: str,
        headers: Dict[str, str],
        body: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[SecurityAlert]:
        """Analyze incoming request for security threats"""

        alerts = []
        current_time = datetime.utcnow()

        # Track IP activity
        self.ip_activity[ip_address].append(current_time)

        # Clean old activity records (keep last hour)
        cutoff_time = current_time - timedelta(hours=1)
        self.ip_activity[ip_address] = [
            timestamp
            for timestamp in self.ip_activity[ip_address]
            if timestamp > cutoff_time
        ]

        # Check for suspicious user agent
        if self._is_suspicious_user_agent(user_agent):
            alert = await self._create_alert(
                ThreatLevel.MEDIUM,
                AttackType.SUSPICIOUS_PATTERN,
                ip_address,
                user_agent,
                "Suspicious user agent detected",
                {"user_agent": user_agent, "endpoint": endpoint},
                user_id=user_id,
                session_id=session_id,
            )
            alerts.append(alert)

        # Check for rate limit abuse
        if len(self.ip_activity[ip_address]) > 100:  # More than 100 requests per hour
            alert = await self._create_alert(
                ThreatLevel.HIGH,
                AttackType.RATE_LIMIT_ABUSE,
                ip_address,
                user_agent,
                "Excessive request rate detected",
                {
                    "requests_per_hour": len(self.ip_activity[ip_address]),
                    "endpoint": endpoint,
                },
                user_id=user_id,
                session_id=session_id,
            )
            alerts.append(alert)

        # Analyze request content
        content_to_analyze = []
        if body:
            content_to_analyze.append(("body", body))

        for header_name, header_value in headers.items():
            content_to_analyze.append((f"header_{header_name}", header_value))

        content_to_analyze.append(("endpoint", endpoint))

        # Check for attack patterns
        for location, content in content_to_analyze:
            if content:
                attack_alerts = await self._detect_attack_patterns(
                    content, ip_address, user_agent, location, user_id, session_id
                )
                alerts.extend(attack_alerts)

        # Check for data exfiltration patterns
        if self._is_data_exfiltration_attempt(endpoint, method, body):
            alert = await self._create_alert(
                ThreatLevel.HIGH,
                AttackType.DATA_EXFILTRATION,
                ip_address,
                user_agent,
                "Potential data exfiltration attempt",
                {"endpoint": endpoint, "method": method},
                user_id=user_id,
                session_id=session_id,
            )
            alerts.append(alert)

        # Store alerts
        self.alerts.extend(alerts)

        # Apply automatic mitigation if needed
        for alert in alerts:
            if alert.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                await self._apply_mitigation(alert)

        return alerts

    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious"""
        if not user_agent:
            return True

        user_agent_lower = user_agent.lower()

        for pattern in self.suspicious_user_agents:
            if re.search(pattern, user_agent_lower):
                return True

        return False

    async def _detect_attack_patterns(
        self,
        content: str,
        ip_address: str,
        user_agent: str,
        location: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[SecurityAlert]:
        """Detect attack patterns in content"""

        alerts = []
        content_lower = content.lower()

        for attack_type, patterns in self.attack_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    # Determine threat level based on attack type
                    threat_level = {
                        AttackType.SQL_INJECTION: ThreatLevel.HIGH,
                        AttackType.XSS_ATTEMPT: ThreatLevel.HIGH,
                        AttackType.PATH_TRAVERSAL: ThreatLevel.HIGH,
                        AttackType.COMMAND_INJECTION: ThreatLevel.CRITICAL,
                        AttackType.PROMPT_INJECTION: ThreatLevel.MEDIUM,
                    }.get(attack_type, ThreatLevel.MEDIUM)

                    alert = await self._create_alert(
                        threat_level,
                        attack_type,
                        ip_address,
                        user_agent,
                        f"{attack_type.value.replace('_', ' ').title()} attempt detected",
                        {
                            "pattern": pattern,
                            "location": location,
                            "content_sample": content[:200],
                        },
                        user_id=user_id,
                        session_id=session_id,
                    )
                    alerts.append(alert)
                    break  # Only one alert per attack type per content

        return alerts

    def _is_data_exfiltration_attempt(
        self, endpoint: str, method: str, body: Optional[str]
    ) -> bool:
        """Check for data exfiltration patterns"""

        # Check for suspicious endpoints
        suspicious_endpoints = [
            "/download/",
            "/export/",
            "/backup/",
            "/dump/",
            "/admin/",
        ]

        if any(suspicious in endpoint.lower() for suspicious in suspicious_endpoints):
            return True

        # Check for bulk data requests
        if body and len(body) > 50000:  # Large request body
            return True

        # Check for multiple file requests
        if "file" in endpoint.lower() and method.upper() == "GET":
            return True

        return False

    async def _create_alert(
        self,
        threat_level: ThreatLevel,
        attack_type: AttackType,
        source_ip: str,
        user_agent: str,
        description: str,
        details: Dict[str, Any],
        affected_resource: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> SecurityAlert:
        """Create a security alert"""

        alert_id = hashlib.md5(
            f"{datetime.utcnow().isoformat()}{source_ip}{attack_type.value}".encode()
        ).hexdigest()[:12]

        alert = SecurityAlert(
            id=alert_id,
            timestamp=datetime.utcnow(),
            threat_level=threat_level,
            attack_type=attack_type,
            source_ip=source_ip,
            user_agent=user_agent,
            description=description,
            details=details,
            affected_resource=affected_resource,
            user_id=user_id,
            session_id=session_id,
        )

        # Log to audit system
        await audit_logger.log_event(
            AuditEvent(
                event_type=AuditEventType.SECURITY_VIOLATION,
                user_id=user_id,
                session_id=session_id,
                ip_address=source_ip,
                user_agent=user_agent,
                details={
                    "alert_id": alert_id,
                    "threat_level": threat_level.value,
                    "attack_type": attack_type.value,
                    "description": description,
                    **details,
                },
                severity={
                    ThreatLevel.LOW: AuditSeverity.LOW,
                    ThreatLevel.MEDIUM: AuditSeverity.MEDIUM,
                    ThreatLevel.HIGH: AuditSeverity.HIGH,
                    ThreatLevel.CRITICAL: AuditSeverity.CRITICAL,
                }[threat_level],
                success=False,
                error_message=description,
            )
        )

        return alert

    async def _apply_mitigation(self, alert: SecurityAlert):
        """Apply automatic mitigation measures"""

        if alert.attack_type == AttackType.RATE_LIMIT_ABUSE:
            # Temporarily block IP
            self.blocked_ips.add(alert.source_ip)
            alert.mitigation_applied = True

        elif alert.attack_type in [
            AttackType.SQL_INJECTION,
            AttackType.COMMAND_INJECTION,
            AttackType.XSS_ATTEMPT,
        ]:
            # Block IP for security violations
            self.blocked_ips.add(alert.source_ip)
            alert.mitigation_applied = True

        elif alert.threat_level == ThreatLevel.CRITICAL:
            # Block IP for critical threats
            self.blocked_ips.add(alert.source_ip)
            alert.mitigation_applied = True

    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked"""
        return ip_address in self.blocked_ips

    def unblock_ip(self, ip_address: str):
        """Unblock an IP address"""
        self.blocked_ips.discard(ip_address)

    def get_recent_alerts(
        self,
        hours: int = 24,
        threat_level: Optional[ThreatLevel] = None,
        attack_type: Optional[AttackType] = None,
    ) -> List[SecurityAlert]:
        """Get recent security alerts"""

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        filtered_alerts = [
            alert for alert in self.alerts if alert.timestamp > cutoff_time
        ]

        if threat_level:
            filtered_alerts = [
                alert for alert in filtered_alerts if alert.threat_level == threat_level
            ]

        if attack_type:
            filtered_alerts = [
                alert for alert in filtered_alerts if alert.attack_type == attack_type
            ]

        return sorted(filtered_alerts, key=lambda x: x.timestamp, reverse=True)

    def get_security_summary(self) -> Dict[str, Any]:
        """Get security monitoring summary"""

        recent_alerts = self.get_recent_alerts(24)

        summary = {
            "monitoring_active": self.monitoring_active,
            "total_alerts_24h": len(recent_alerts),
            "blocked_ips": len(self.blocked_ips),
            "alerts_by_threat_level": {
                level.value: len([a for a in recent_alerts if a.threat_level == level])
                for level in ThreatLevel
            },
            "alerts_by_attack_type": {
                attack.value: len([a for a in recent_alerts if a.attack_type == attack])
                for attack in AttackType
            },
            "top_attacking_ips": self._get_top_attacking_ips(recent_alerts),
            "mitigation_effectiveness": self._calculate_mitigation_effectiveness(
                recent_alerts
            ),
        }

        return summary

    def _get_top_attacking_ips(
        self, alerts: List[SecurityAlert], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top attacking IP addresses"""

        ip_counts = defaultdict(int)
        ip_threat_levels = defaultdict(list)

        for alert in alerts:
            ip_counts[alert.source_ip] += 1
            ip_threat_levels[alert.source_ip].append(alert.threat_level)

        top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

        result = []
        for ip, count in top_ips:
            threat_levels = ip_threat_levels[ip]
            max_threat = max(
                threat_levels,
                key=lambda x: ["low", "medium", "high", "critical"].index(x.value),
            )

            result.append(
                {
                    "ip": ip,
                    "alert_count": count,
                    "max_threat_level": max_threat.value,
                    "is_blocked": ip in self.blocked_ips,
                }
            )

        return result

    def _calculate_mitigation_effectiveness(
        self, alerts: List[SecurityAlert]
    ) -> Dict[str, Any]:
        """Calculate mitigation effectiveness"""

        total_alerts = len(alerts)
        mitigated_alerts = len([a for a in alerts if a.mitigation_applied])

        if total_alerts == 0:
            return {"effectiveness_rate": 0, "total_alerts": 0, "mitigated_alerts": 0}

        effectiveness_rate = (mitigated_alerts / total_alerts) * 100

        return {
            "effectiveness_rate": round(effectiveness_rate, 2),
            "total_alerts": total_alerts,
            "mitigated_alerts": mitigated_alerts,
        }


# Global security monitor instance
security_monitor = SecurityMonitor()


async def analyze_request_security(
    ip_address: str,
    user_agent: str,
    endpoint: str,
    method: str,
    headers: Dict[str, str],
    body: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> List[SecurityAlert]:
    """Analyze request for security threats"""

    return await security_monitor.analyze_request(
        ip_address=ip_address,
        user_agent=user_agent,
        endpoint=endpoint,
        method=method,
        headers=headers,
        body=body,
        user_id=user_id,
        session_id=session_id,
    )


def is_request_blocked(ip_address: str) -> bool:
    """Check if request should be blocked"""
    return security_monitor.is_ip_blocked(ip_address)
