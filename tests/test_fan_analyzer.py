import pytest
import time
from loq_control.core.fan_analyzer import FanAnalyzer

def test_fan_analyzer_learns_equilibrium():
    analyzer = FanAnalyzer()
    
    # Simulate 40 seconds of stable load
    # 35W, 40% PWM, 70C
    for _ in range(40):
        analyzer.record_tick(wattage=35.2, pwm=40, temp=70.1)
        
    # Check if learned
    # 35W should be in bin 35
    assert 35 in analyzer.equilibrium_map
    point = analyzer.equilibrium_map[35]
    assert point.pwm == 40
    assert abs(point.temp - 70.1) < 0.1

def test_fan_analyzer_ignores_unstable_load():
    analyzer = FanAnalyzer()
    
    # Temperature oscillating rapidly
    for i in range(40):
        temp = 70.0 if i % 2 == 0 else 75.0
        analyzer.record_tick(wattage=35.0, pwm=40, temp=temp)
        
    assert 35 not in analyzer.equilibrium_map

def test_fan_analyzer_prediction():
    analyzer = FanAnalyzer()
    
    # Feed stable data
    for _ in range(40):
        analyzer.record_tick(wattage=50.0, pwm=60, temp=80.0)
        
    # Predict for 50W
    prediction = analyzer.get_predicted_pwm(50.0)
    assert prediction == 60
    
    # No prediction for unknown wattage
    assert analyzer.get_predicted_pwm(10.0) is None
