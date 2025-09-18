"""
Advanced Performance Optimization Example for FastAPI Microservices SDK.

This example demonstrates how to use the advanced performance optimization
system with ML-based recommendations, impact analysis, and resource optimization.

Author: FastAPI Microservices SDK
Version: 1.0.0
"""

import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from fastapi_microservices_sdk.observability.optimization import (
    AdvancedOptimizationManager,
    OptimizationConfig,
    RecommendationConfig,
    ImpactAnalysisConfig,
    ResourceOptimizationConfig,
    create_optimization_manager,
    OptimizationStrategy,
    OptimizationObjective,
    ChangeType
)


async def main():
    """Main optimization example function."""
    print("🚀 FastAPI Microservices SDK - Advanced Performance Optimization Example")
    print("=" * 70)
    
    # 1. Create optimization configuration
    config = OptimizationConfig(
        service_name="example-service",
        service_version="1.0.0",
        environment="development",
        enabled=True,
        optimization_strategy=OptimizationStrategy.BALANCED,
        
        # Recommendation configuration
        recommendations=RecommendationConfig(
            enabled=True,
            min_confidence_threshold=0.7,
            max_recommendations_per_analysis=5,
            use_ml_recommendations=True
        ),
        
        # Impact analysis configuration
        impact_analysis=ImpactAnalysisConfig(
            enabled=True,
            baseline_comparison_window=timedelta(hours=2),
            track_deployment_impact=True,
            generate_impact_reports=True
        ),
        
        # Resource optimization configuration
        resource_optimization=ResourceOptimizationConfig(
            enabled=True,
            optimization_algorithm="genetic_algorithm",
            use_ml_optimization=True,
            optimize_for_performance=True,
            optimize_for_cost=True
        )
    )
    
    # 2. Create and start optimization manager
    print("\\n🔧 Starting Advanced Optimization Manager...")
    optimization_manager = create_optimization_manager(config)
    
    # Add callbacks for monitoring
    async def optimization_callback(event_type: str, event_data: Dict[str, Any]):
        print(f"📊 Optimization Event: {event_type}")
        if event_type == "recommendations_generated":
            print(f"   Generated {event_data['count']} recommendations")
    
    async def alert_callback(alert_message: str):
        print(f"🚨 Optimization Alert: {alert_message}")
    
    optimization_manager.add_optimization_callback(optimization_callback)
    optimization_manager.add_alert_callback(alert_callback)
    
    await optimization_manager.start()
    
    try:
        # 3. Simulate performance data collection
        print("\\n📈 Collecting performance data...")
        
        # Simulate normal performance metrics
        for i in range(60):
            timestamp = datetime.now(timezone.utc) - timedelta(minutes=60-i)
            
            # Response time (normal: 200-400ms)
            response_time = random.normalvariate(300, 50)
            await optimization_manager.record_performance_metric(
                "api_response_time", 
                max(100, response_time), 
                timestamp
            )
            
            # Throughput (normal: 80-120 RPS)
            throughput = random.normalvariate(100, 15)
            await optimization_manager.record_performance_metric(
                "api_throughput", 
                max(50, throughput), 
                timestamp
            )
            
            # Error rate (normal: 0.5-2%)
            error_rate = random.normalvariate(1.0, 0.3)
            await optimization_manager.record_performance_metric(
                "api_error_rate", 
                max(0, min(5, error_rate)), 
                timestamp
            )
            
            # CPU usage (normal: 40-60%)
            cpu_usage = random.normalvariate(50, 8)
            await optimization_manager.record_resource_metric(
                "server", 
                "cpu", 
                max(10, min(100, cpu_usage)), 
                timestamp
            )
            
            # Memory usage (normal: 60-80%)
            memory_usage = random.normalvariate(70, 10)
            await optimization_manager.record_resource_metric(
                "server", 
                "memory", 
                max(20, min(100, memory_usage)), 
                timestamp
            )
        
        print("✅ Performance data collected")
        
        # 4. Generate optimization recommendations
        print("\\n🎯 Generating optimization recommendations...")
        
        recommendations = await optimization_manager.generate_optimization_recommendations()
        
        print(f"Generated {len(recommendations)} recommendations:")
        for i, rec in enumerate(recommendations[:3], 1):  # Show first 3
            print(f"  {i}. {rec.title}")
            print(f"     Priority: {rec.priority.value}, Confidence: {rec.confidence_score:.1%}")
            print(f"     Expected gain: {rec.estimated_performance_gain:.1f}%")
            print(f"     Cost impact: {rec.estimated_cost_impact:+.1f}%")
            print(f"     Complexity: {rec.implementation_complexity.value}")
        
        # 5. Simulate deployment and impact analysis
        print("\\n🚀 Simulating deployment and impact analysis...")
        
        deployment_id = "deploy_v1.1.0"
        await optimization_manager.register_deployment(
            deployment_id,
            "Performance optimization deployment with caching improvements"
        )
        
        # Simulate post-deployment performance (with improvement)
        print("   Collecting post-deployment performance data...")
        for i in range(20):
            timestamp = datetime.now(timezone.utc)
            
            # Improved response time (15% better)
            response_time = random.normalvariate(255, 40)  # 15% improvement
            await optimization_manager.record_performance_metric(
                "api_response_time", 
                max(80, response_time), 
                timestamp
            )
            
            # Improved throughput (10% better)
            throughput = random.normalvariate(110, 15)  # 10% improvement
            await optimization_manager.record_performance_metric(
                "api_throughput", 
                max(60, throughput), 
                timestamp
            )
            
            await asyncio.sleep(0.1)  # Small delay between metrics
        
        # Wait for impact analysis to be scheduled and run
        print("   Waiting for impact analysis...")
        await asyncio.sleep(2)
        
        # Analyze deployment impact
        impact_result = await optimization_manager.analyze_deployment_impact(deployment_id)
        
        if impact_result:
            print(f"\\n📊 Impact Analysis Results:")
            print(f"   Overall Impact: {impact_result.overall_impact_type.value}")
            print(f"   Impact Score: {impact_result.impact_score:+.1f}")
            print(f"   Response Time Impact: {impact_result.change_impact.response_time_impact:+.1f}%")
            print(f"   Throughput Impact: {impact_result.change_impact.throughput_impact:+.1f}%")
            print(f"   Rollback Recommended: {impact_result.rollback_recommended}")
            
            if impact_result.recommendations:
                print("   Recommendations:")
                for rec in impact_result.recommendations:
                    print(f"     • {rec}")
        
        # 6. Resource optimization
        print("\\n⚙️  Performing resource optimization...")
        
        # Optimize for balanced performance and cost
        optimization_result = await optimization_manager.optimize_resources(
            OptimizationObjective.BALANCED
        )
        
        print(f"Resource Optimization Results:")
        print(f"   Objective: {optimization_result.optimization_objective.value}")
        print(f"   Improvement: {optimization_result.improvement_percentage:+.1f}%")
        print(f"   Confidence: {optimization_result.confidence_score:.1%}")
        
        print(f"\\n   Current Allocation:")
        current = optimization_result.current_allocation
        print(f"     CPU: {current.cpu_cores} cores")
        print(f"     Memory: {current.memory_mb}MB")
        print(f"     Cost: ${current.estimated_cost:.2f}")
        print(f"     Performance Score: {current.estimated_performance_score:.1f}")
        
        print(f"\\n   Optimized Allocation:")
        optimized = optimization_result.optimized_allocation
        print(f"     CPU: {optimized.cpu_cores} cores")
        print(f"     Memory: {optimized.memory_mb}MB")
        print(f"     Cost: ${optimized.estimated_cost:.2f}")
        print(f"     Performance Score: {optimized.estimated_performance_score:.1f}")
        
        print(f"\\n   Implementation Steps:")
        for i, step in enumerate(optimization_result.implementation_steps, 1):
            print(f"     {i}. {step}")
        
        # 7. Implement a recommendation
        print("\\n✅ Implementing optimization recommendation...")
        
        if recommendations:
            first_rec = recommendations[0]
            implementation_result = {
                'status': 'success',
                'implementation_time': datetime.now(timezone.utc).isoformat(),
                'performance_improvement_observed': 12.5,
                'cost_impact_actual': -5.0,  # 5% cost reduction
                'notes': 'Successfully implemented caching optimization'
            }
            
            await optimization_manager.implement_recommendation(
                first_rec.recommendation_id,
                implementation_result
            )
            
            print(f"   Implemented: {first_rec.title}")
            print(f"   Observed improvement: {implementation_result['performance_improvement_observed']}%")
            print(f"   Cost impact: {implementation_result['cost_impact_actual']:+.1f}%")
        
        # 8. Get comprehensive optimization summary
        print("\\n📊 Optimization System Summary:")
        summary = await optimization_manager.get_optimization_summary()
        
        print(f"System Status: {summary['system_status']}")
        print(f"Optimization Strategy: {summary['optimization_strategy']}")
        
        print("\\nStatistics:")
        stats = summary['statistics']
        print(f"   Recommendations Generated: {stats['recommendations_generated']}")
        print(f"   Optimizations Applied: {stats['optimizations_applied']}")
        print(f"   Performance Improvements: {stats['performance_improvements']}")
        print(f"   Cost Savings: ${stats['cost_savings']:.2f}")
        
        print("\\nComponent Health:")
        components = summary['components']
        for component, health in components.items():
            status = "✅" if health.get('is_running', False) else "❌"
            print(f"   {status} {component}")
        
        # 9. Demonstrate different optimization objectives
        print("\\n🎯 Testing different optimization objectives...")
        
        objectives = [
            (OptimizationObjective.PERFORMANCE, "Performance-focused"),
            (OptimizationObjective.COST, "Cost-focused"),
            (OptimizationObjective.RELIABILITY, "Reliability-focused")
        ]
        
        for objective, description in objectives:
            result = await optimization_manager.optimize_resources(objective)
            print(f"\\n   {description} Optimization:")
            print(f"     Improvement: {result.improvement_percentage:+.1f}%")
            print(f"     CPU: {result.current_allocation.cpu_cores} → {result.optimized_allocation.cpu_cores} cores")
            print(f"     Cost: ${result.current_allocation.estimated_cost:.2f} → ${result.optimized_allocation.estimated_cost:.2f}")
        
        # 10. Wait for background processing
        print("\\n⏰ Waiting for background processing...")
        await asyncio.sleep(3)
        
        print("\\n✅ Advanced optimization example completed successfully!")
        
        # Show final statistics
        final_summary = await optimization_manager.get_optimization_summary()
        final_stats = final_summary['statistics']
        print("\\n📈 Final Statistics:")
        print(f"   Total Recommendations: {final_stats['recommendations_generated']}")
        print(f"   Total Optimizations: {final_stats['optimizations_applied']}")
        print(f"   Performance Improvements: {final_stats['performance_improvements']}")
        print(f"   Total Cost Savings: ${final_stats['cost_savings']:.2f}")
        
    except Exception as e:
        print(f"❌ Error in optimization example: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean shutdown
        print("\\n🛑 Shutting down optimization manager...")
        await optimization_manager.stop()


async def demonstrate_advanced_optimization_features():
    """Demonstrate advanced optimization features."""
    print("\\n🎓 Advanced Optimization Features Demonstration")
    print("=" * 60)
    
    # Create configuration for advanced features
    config = OptimizationConfig(
        service_name="advanced-optimization-service",
        enabled=True,
        optimization_strategy=OptimizationStrategy.PERFORMANCE_FIRST,
        optimization_aggressiveness=0.8  # High aggressiveness
    )
    
    optimization_manager = create_optimization_manager(config)
    await optimization_manager.start()
    
    try:
        # 1. Simulate high-load scenario
        print("🔥 High-Load Scenario Simulation...")
        
        # Simulate high resource usage
        for i in range(30):
            timestamp = datetime.now(timezone.utc)
            
            # High CPU usage (85-95%)
            cpu_usage = random.uniform(85, 95)
            await optimization_manager.record_resource_metric("server", "cpu", cpu_usage, timestamp)
            
            # High memory usage (90-98%)
            memory_usage = random.uniform(90, 98)
            await optimization_manager.record_resource_metric("server", "memory", memory_usage, timestamp)
            
            # Degraded response time (800-1200ms)
            response_time = random.uniform(800, 1200)
            await optimization_manager.record_performance_metric("api_response_time", response_time, timestamp)
        
        # Generate recommendations for high-load scenario
        recommendations = await optimization_manager.generate_optimization_recommendations()
        
        print(f"Generated {len(recommendations)} recommendations for high-load scenario:")
        for rec in recommendations:
            print(f"  🎯 {rec.title}")
            print(f"     Priority: {rec.priority.value}")
            print(f"     Expected Performance Gain: {rec.estimated_performance_gain:.1f}%")
            print(f"     Implementation Complexity: {rec.implementation_complexity.value}")
        
        # 2. Simulate multiple deployments with different impacts
        print("\\n🚀 Multiple Deployment Impact Analysis...")
        
        deployments = [
            ("deploy_cache_optimization", "Implemented Redis caching", 15),  # 15% improvement
            ("deploy_db_indexing", "Added database indexes", 25),           # 25% improvement
            ("deploy_algorithm_change", "Changed sorting algorithm", -10)    # 10% degradation
        ]
        
        for deploy_id, description, impact_percent in deployments:
            # Register deployment
            await optimization_manager.register_deployment(deploy_id, description)
            
            # Simulate post-deployment performance
            base_response_time = 300
            new_response_time = base_response_time * (1 - impact_percent / 100)
            
            for i in range(10):
                response_time = random.normalvariate(new_response_time, 30)
                await optimization_manager.record_performance_metric(
                    "api_response_time", 
                    max(50, response_time)
                )
            
            # Analyze impact
            impact_result = await optimization_manager.analyze_deployment_impact(deploy_id)
            
            if impact_result:
                print(f"\\n   📊 {deploy_id}:")
                print(f"      Impact Type: {impact_result.overall_impact_type.value}")
                print(f"      Impact Score: {impact_result.impact_score:+.1f}")
                print(f"      Rollback Recommended: {impact_result.rollback_recommended}")
        
        # 3. Resource optimization with different strategies
        print("\\n⚙️  Advanced Resource Optimization Strategies...")
        
        strategies = [
            OptimizationObjective.PERFORMANCE,
            OptimizationObjective.COST,
            OptimizationObjective.BALANCED
        ]
        
        for strategy in strategies:
            result = await optimization_manager.optimize_resources(strategy)
            
            print(f"\\n   {strategy.value.title()} Optimization:")
            print(f"      Improvement: {result.improvement_percentage:+.1f}%")
            print(f"      Confidence: {result.confidence_score:.1%}")
            
            current = result.current_allocation
            optimized = result.optimized_allocation
            
            cpu_change = ((optimized.cpu_cores - current.cpu_cores) / current.cpu_cores) * 100
            memory_change = ((optimized.memory_mb - current.memory_mb) / current.memory_mb) * 100
            cost_change = ((optimized.estimated_cost - current.estimated_cost) / current.estimated_cost) * 100
            
            print(f"      CPU Change: {cpu_change:+.1f}%")
            print(f"      Memory Change: {memory_change:+.1f}%")
            print(f"      Cost Change: {cost_change:+.1f}%")
        
        print("\\n🎉 Advanced optimization features demonstration completed!")
        
    finally:
        await optimization_manager.stop()


if __name__ == "__main__":
    # Run the main optimization example
    asyncio.run(main())
    
    # Run advanced features demonstration
    asyncio.run(demonstrate_advanced_optimization_features())