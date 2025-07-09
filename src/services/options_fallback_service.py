#!/usr/bin/env python3

import logging
import requests
import json
from typing import Dict, Optional, List
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class OptionsFallbackService:
    """Service to provide fallback options data when primary source fails"""
    
    def __init__(self):
        self.primary_source = "yahoo_finance"
        self.fallback_sources = []
        self.oi_warning_threshold = 0.1  # Warn if less than 10% of options have OI
        
    def check_oi_data_quality(self, options_data: Dict) -> Dict:
        """Check the quality of open interest data and provide warnings"""
        quality_report = {
            'has_data': False,
            'total_options': 0,
            'options_with_oi': 0,
            'options_with_zero_oi': 0,
            'options_with_null_oi': 0,
            'oi_coverage_percentage': 0.0,
            'warnings': [],
            'recommendations': []
        }
        
        try:
            total_options = 0
            options_with_oi = 0
            options_with_zero_oi = 0
            options_with_null_oi = 0
            
            for expiry, chain_data in options_data.items():
                calls = chain_data.get('calls', [])
                puts = chain_data.get('puts', [])
                
                for call in calls:
                    total_options += 1
                    oi = call.get('openInterest')
                    if oi is None:
                        options_with_null_oi += 1
                    elif oi == 0:
                        options_with_zero_oi += 1
                    else:
                        options_with_oi += 1
                
                for put in puts:
                    total_options += 1
                    oi = put.get('openInterest')
                    if oi is None:
                        options_with_null_oi += 1
                    elif oi == 0:
                        options_with_zero_oi += 1
                    else:
                        options_with_oi += 1
            
            quality_report.update({
                'has_data': total_options > 0,
                'total_options': total_options,
                'options_with_oi': options_with_oi,
                'options_with_zero_oi': options_with_zero_oi,
                'options_with_null_oi': options_with_null_oi,
                'oi_coverage_percentage': (options_with_oi / total_options * 100) if total_options > 0 else 0
            })
            
            # Generate warnings and recommendations
            if quality_report['oi_coverage_percentage'] < self.oi_warning_threshold * 100:
                quality_report['warnings'].append(
                    f"Low OI data coverage: {quality_report['oi_coverage_percentage']:.1f}% of options have OI data"
                )
                quality_report['recommendations'].append(
                    "Consider using a different data source or checking data availability"
                )
            
            if options_with_null_oi > 0:
                quality_report['warnings'].append(
                    f"{options_with_null_oi} options have missing OI data (null values)"
                )
            
            if options_with_zero_oi > 0:
                quality_report['warnings'].append(
                    f"{options_with_zero_oi} options have zero OI (may indicate no open contracts)"
                )
            
            if not quality_report['warnings']:
                quality_report['warnings'].append("OI data quality appears good")
            
        except Exception as e:
            logging.error(f"Error checking OI data quality: {e}")
            quality_report['warnings'].append(f"Error analyzing OI data: {str(e)}")
        
        return quality_report
    
    def get_oi_summary(self, options_data: Dict) -> Dict:
        """Get a summary of open interest data for display"""
        summary = {
            'total_expirations': len(options_data),
            'expirations': {},
            'overall_stats': {
                'total_options': 0,
                'options_with_oi': 0,
                'options_with_zero_oi': 0,
                'options_with_null_oi': 0
            }
        }
        
        for expiry, chain_data in options_data.items():
            calls = chain_data.get('calls', [])
            puts = chain_data.get('puts', [])
            
            expiry_stats = {
                'calls': len(calls),
                'puts': len(puts),
                'calls_with_oi': sum(1 for c in calls if c.get('openInterest') is not None and c.get('openInterest', 0) > 0),
                'puts_with_oi': sum(1 for p in puts if p.get('openInterest') is not None and p.get('openInterest', 0) > 0),
                'calls_with_zero_oi': sum(1 for c in calls if c.get('openInterest') == 0),
                'puts_with_zero_oi': sum(1 for p in puts if p.get('openInterest') == 0),
                'calls_with_null_oi': sum(1 for c in calls if c.get('openInterest') is None),
                'puts_with_null_oi': sum(1 for p in puts if p.get('openInterest') is None)
            }
            
            summary['expirations'][expiry] = expiry_stats
            
            # Update overall stats
            summary['overall_stats']['total_options'] += len(calls) + len(puts)
            summary['overall_stats']['options_with_oi'] += expiry_stats['calls_with_oi'] + expiry_stats['puts_with_oi']
            summary['overall_stats']['options_with_zero_oi'] += expiry_stats['calls_with_zero_oi'] + expiry_stats['puts_with_zero_oi']
            summary['overall_stats']['options_with_null_oi'] += expiry_stats['calls_with_null_oi'] + expiry_stats['puts_with_null_oi']
        
        return summary
    
    def suggest_alternative_sources(self, ticker: str) -> List[str]:
        """Suggest alternative data sources for options data"""
        suggestions = [
            {
                'name': 'Polygon.io',
                'description': 'Free tier with 5 calls/minute, 100 calls/day',
                'url': 'https://polygon.io/docs/options/get_v3_reference_options_contracts',
                'requires_api_key': True,
                'free_tier': True
            },
            {
                'name': 'IEX Cloud',
                'description': 'Free tier with 50,000 messages/month',
                'url': 'https://iexcloud.io/docs/api/',
                'requires_api_key': True,
                'free_tier': True
            },
            {
                'name': 'MarketStack',
                'description': 'Free tier with 1,000 API calls/month',
                'url': 'https://marketstack.com/documentation',
                'requires_api_key': True,
                'free_tier': True
            },
            {
                'name': 'Barchart.com',
                'description': 'Free web scraping (requires implementation)',
                'url': 'https://www.barchart.com/stocks/quotes/',
                'requires_api_key': False,
                'free_tier': True
            }
        ]
        
        return suggestions
    
    def create_oi_warning_message(self, quality_report: Dict) -> str:
        """Create a user-friendly warning message about OI data quality"""
        if not quality_report['warnings']:
            return "Open Interest data quality appears good."
        
        message_parts = []
        
        if quality_report['oi_coverage_percentage'] < 10:
            message_parts.append(
                f"⚠️ Low Open Interest Coverage: Only {quality_report['oi_coverage_percentage']:.1f}% of options have OI data."
            )
        
        if quality_report['options_with_null_oi'] > 0:
            message_parts.append(
                f"⚠️ {quality_report['options_with_null_oi']} options have missing OI data (shown as 0*)."
            )
        
        if quality_report['options_with_zero_oi'] > 0:
            message_parts.append(
                f"ℹ️ {quality_report['options_with_zero_oi']} options have zero OI (no open contracts)."
            )
        
        if quality_report['recommendations']:
            message_parts.append("💡 " + quality_report['recommendations'][0])
        
        return " ".join(message_parts)
    
    def enhance_options_data_with_warnings(self, options_data: Dict, ticker: str) -> Dict:
        """Enhance options data with quality warnings and metadata"""
        quality_report = self.check_oi_data_quality(options_data)
        oi_summary = self.get_oi_summary(options_data)
        
        enhanced_data = {
            'options_data': options_data,
            'quality_report': quality_report,
            'oi_summary': oi_summary,
            'warning_message': self.create_oi_warning_message(quality_report),
            'alternative_sources': self.suggest_alternative_sources(ticker),
            'metadata': {
                'ticker': ticker,
                'generated_at': datetime.now().isoformat(),
                'data_source': self.primary_source,
                'has_quality_issues': len(quality_report['warnings']) > 1  # More than just "appears good"
            }
        }
        
        return enhanced_data

# Test function
def test_fallback_service():
    """Test the fallback service with sample data"""
    service = OptionsFallbackService()
    
    # Create sample options data with mixed OI quality
    sample_data = {
        "2025-07-11": {
            "calls": [
                {"strike": 450, "openInterest": 1000, "lastPrice": 5.0},
                {"strike": 460, "openInterest": 0, "lastPrice": 3.0},
                {"strike": 470, "openInterest": None, "lastPrice": 1.0},
                {"strike": 480, "openInterest": 500, "lastPrice": 0.5}
            ],
            "puts": [
                {"strike": 450, "openInterest": 800, "lastPrice": 2.0},
                {"strike": 460, "openInterest": 0, "lastPrice": 4.0},
                {"strike": 470, "openInterest": None, "lastPrice": 6.0}
            ]
        }
    }
    
    print("Testing Options Fallback Service...")
    
    # Test quality check
    quality_report = service.check_oi_data_quality(sample_data)
    print(f"\nQuality Report:")
    print(f"  Total options: {quality_report['total_options']}")
    print(f"  Options with OI: {quality_report['options_with_oi']}")
    print(f"  Options with zero OI: {quality_report['options_with_zero_oi']}")
    print(f"  Options with null OI: {quality_report['options_with_null_oi']}")
    print(f"  OI coverage: {quality_report['oi_coverage_percentage']:.1f}%")
    
    # Test warning message
    warning_message = service.create_oi_warning_message(quality_report)
    print(f"\nWarning Message: {warning_message}")
    
    # Test enhanced data
    enhanced_data = service.enhance_options_data_with_warnings(sample_data, "SPY")
    print(f"\nEnhanced data keys: {list(enhanced_data.keys())}")
    print(f"Has quality issues: {enhanced_data['metadata']['has_quality_issues']}")

if __name__ == "__main__":
    test_fallback_service() 