#!/usr/bin/env python3
"""
Performance Monitoring Script for WolfAssistants
Monitors endpoint performance and identifies slow endpoints.

Usage:
    python performance_monitor.py
    python performance_monitor.py --threshold 0.5 --limit 20
    python performance_monitor.py --endpoint "POST /api/v1/auth/login"
"""
import sys
import os
import argparse
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app.middleware.performance_monitoring import get_performance_stats, get_slow_endpoints


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f}μs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f}ms"
    else:
        return f"{seconds:.3f}s"


def print_performance_report(threshold: float = 1.0, limit: int = 10, endpoint_filter: str = None):
    """Print a formatted performance report."""
    print("=" * 80)
    print("WolfAssistants Performance Monitoring Report")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get all stats
    all_stats = get_performance_stats()
    
    if not all_stats:
        print("⚠️  No performance data available yet.")
        print("   Make some API requests and run this script again.")
        return
    
    # Filter by endpoint if specified
    if endpoint_filter:
        all_stats = {
            k: v for k, v in all_stats.items()
            if endpoint_filter.lower() in k.lower()
        }
        if not all_stats:
            print(f"⚠️  No endpoints found matching '{endpoint_filter}'")
            return
    
    # Get slow endpoints
    slow_endpoints = get_slow_endpoints(threshold=threshold, limit=limit)
    
    # Summary
    total_requests = sum(s["count"] for s in all_stats.values())
    total_endpoints = len(all_stats)
    slow_count = len(slow_endpoints)
    
    print("📊 Summary")
    print("-" * 80)
    print(f"  Total Endpoints Monitored: {total_endpoints}")
    print(f"  Total Requests: {total_requests:,}")
    print(f"  Slow Endpoints (>={threshold}s): {slow_count}")
    print()
    
    # Slow endpoints section
    if slow_endpoints:
        print("🐌 Slow Endpoints (Requires Attention)")
        print("-" * 80)
        print(f"{'Endpoint':<50} {'Avg':<10} {'P95':<10} {'Max':<10} {'Errors':<8} {'Count':<8}")
        print("-" * 80)
        
        for endpoint_data in slow_endpoints:
            endpoint = endpoint_data["endpoint"]
            avg = endpoint_data["avg_duration"]
            p95 = endpoint_data["p95_duration"]
            max_dur = endpoint_data["max_duration"]
            errors = endpoint_data["error_count"]
            count = endpoint_data["count"]
            error_rate = endpoint_data["error_rate"]
            
            # Truncate long endpoint names
            display_endpoint = endpoint[:48] + ".." if len(endpoint) > 50 else endpoint
            
            error_indicator = "⚠️" if error_rate > 0.05 else ""
            
            print(
                f"{display_endpoint:<50} "
                f"{format_duration(avg):<10} "
                f"{format_duration(p95):<10} "
                f"{format_duration(max_dur):<10} "
                f"{errors:<8} "
                f"{count:<8} {error_indicator}"
            )
        print()
    else:
        print("✅ No slow endpoints found (all endpoints are performing well)")
        print()
    
    # All endpoints (sorted by average duration)
    print("📈 All Endpoints (Sorted by Average Duration)")
    print("-" * 80)
    print(f"{'Endpoint':<50} {'Avg':<10} {'Min':<10} {'Max':<10} {'Count':<8}")
    print("-" * 80)
    
    sorted_endpoints = sorted(
        all_stats.items(),
        key=lambda x: x[1]["avg_duration"],
        reverse=True
    )
    
    for endpoint, stats in sorted_endpoints[:limit * 2]:  # Show more endpoints
        # Truncate long endpoint names
        display_endpoint = endpoint[:48] + ".." if len(endpoint) > 50 else endpoint
        
        print(
            f"{display_endpoint:<50} "
            f"{format_duration(stats['avg_duration']):<10} "
            f"{format_duration(stats['min_duration']):<10} "
            f"{format_duration(stats['max_duration']):<10} "
            f"{stats['count']:<8}"
        )
    
    print()
    print("=" * 80)
    print("💡 Tips:")
    print("  - Endpoints with avg > 1s should be optimized")
    print("  - Check P95 duration for worst-case performance")
    print("  - High error rates indicate reliability issues")
    print("  - Use --endpoint flag to filter specific endpoints")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Monitor WolfAssistants API performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python performance_monitor.py
  python performance_monitor.py --threshold 0.5 --limit 20
  python performance_monitor.py --endpoint "POST /api/v1/auth/login"
        """
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=1.0,
        help="Threshold for slow endpoints in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of slow endpoints to show (default: 10)"
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default=None,
        help="Filter endpoints by name (case-insensitive)"
    )
    
    args = parser.parse_args()
    
    try:
        print_performance_report(
            threshold=args.threshold,
            limit=args.limit,
            endpoint_filter=args.endpoint
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Monitoring interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

