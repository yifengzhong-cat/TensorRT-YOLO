#!/usr/bin/env python3
"""
完整示例：展示 MengDong Cloud Analysis Service 的所有功能
"""
import sys
import time
import base64
from pathlib import Path

# 确保 client.py 在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from client import MengDongCloudClient, AnalysisResult
except ImportError:
    print("Error: Could not import client library")
    print("Make sure client.py is in ../src/ directory")
    sys.exit(1)


def example_1_service_status():
    """示例1: 检查服务状态"""
    print("=" * 60)
    print("示例1: 检查服务状态")
    print("=" * 60)
    
    client = MengDongCloudClient("http://localhost:22266")
    
    # 健康检查
    is_healthy = client.health_check()
    print(f"\n服务健康状态: {'✓ 健康' if is_healthy else '✗ 异常'}")
    
    if not is_healthy:
        print("服务未运行，请先启动服务")
        return False
    
    # 获取详细状态
    status = client.get_status()
    print(f"\n详细状态:")
    print(f"  运行状态: {status['status']}")
    print(f"  活跃视频流: {status['active_streams']}/{status['max_streams']}")
    print(f"  已加载模型: {status['loaded_models']}")
    print(f"  时间戳: {status['timestamp']}")
    
    return True


def example_2_list_algorithms():
    """示例2: 获取算法能力列表"""
    print("\n" + "=" * 60)
    print("示例2: 获取算法能力列表")
    print("=" * 60)
    
    client = MengDongCloudClient("http://localhost:22266")
    
    try:
        abilities = client.get_abilities()
        print(f"\n可用算法数量: {len(abilities)}")
        
        for i, ability in enumerate(abilities, 1):
            print(f"\n算法 {i}:")
            print(f"  编码: {ability['algCode']}")
            print(f"  描述: {ability['algDesc']}")
            print(f"  参数:")
            for param in ability.get('algParams', []):
                print(f"    - {param['key']}: {param['value']}")
        
        return True
    except Exception as e:
        print(f"✗ 获取算法列表失败: {e}")
        return False


def example_3_analyze_image():
    """示例3: 图片分析"""
    print("\n" + "=" * 60)
    print("示例3: 图片分析")
    print("=" * 60)
    
    # 检查是否有测试图片
    test_image = Path("test.jpg")
    if not test_image.exists():
        print(f"\n⚠ 测试图片不存在: {test_image}")
        print("请准备一张测试图片命名为 test.jpg")
        print("跳过此示例...")
        return False
    
    client = MengDongCloudClient("http://localhost:22266")
    
    try:
        print(f"\n正在分析图片: {test_image}")
        
        # 使用不同灵敏度进行分析
        for sensitivity in [1, 3, 5]:
            print(f"\n灵敏度 {sensitivity}:")
            result = client.analyze_image(
                test_image,
                alg_code="010101",  # 人员及安全装备检测
                sensitivity=sensitivity
            )
            
            print(f"  分析时间: {result.analyse_time}")
            print(f"  检测数量: {len(result.detections)}")
            
            if result.detections:
                print(f"  检测结果:")
                for det in result.detections[:5]:  # 只显示前5个
                    print(f"    - {det.class_name}: {det.confidence:.2f}% at {det.bbox}")
            
            # 保存结果图片
            output_path = f"result_sensitivity_{sensitivity}.jpg"
            client.save_result_image(result, output_path, use_osd=True)
            print(f"  结果已保存: {output_path}")
        
        return True
    except Exception as e:
        print(f"✗ 图片分析失败: {e}")
        return False


def main():
    """运行所有示例"""
    print("=" * 60)
    print("MengDong Cloud Analysis Service - 完整示例")
    print("=" * 60)
    print("\n此脚本将演示主要功能")
    print("请确保服务已经运行在 http://localhost:22266\n")
    
    input("按 Enter 键开始...")
    
    examples = [
        ("检查服务状态", example_1_service_status),
        ("获取算法列表", example_2_list_algorithms),
        ("图片分析", example_3_analyze_image),
    ]
    
    results = []
    
    for name, example_func in examples:
        try:
            success = example_func()
            results.append((name, success))
        except KeyboardInterrupt:
            print("\n\n用户中断")
            break
        except Exception as e:
            print(f"\n✗ 示例执行失败: {e}")
            results.append((name, False))
        
        # 暂停一下
        if example_func != examples[-1][1]:
            print("\n" + "-" * 60)
            time.sleep(2)
    
    # 总结
    print("\n" + "=" * 60)
    print("示例执行总结")
    print("=" * 60)
    
    for name, success in results:
        status = "✓ 成功" if success else "✗ 失败"
        print(f"{status}: {name}")
    
    successful = sum(1 for _, success in results if success)
    print(f"\n总计: {successful}/{len(results)} 个示例成功")
    
    print("\n" + "=" * 60)
    print("更多信息:")
    print("  - API文档: ../API_GUIDE.md")
    print("  - 部署文档: ../DEPLOYMENT.md")
    print("  - 快速开始: ../QUICKSTART.md")
    print("=" * 60)


if __name__ == "__main__":
    main()
