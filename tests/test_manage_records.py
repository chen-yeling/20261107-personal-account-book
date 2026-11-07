import os
import sys
import pytest
from unittest.mock import patch

# 把项目根目录加入路径，防止找不到 manage_records
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import manage_records

# 准备一条虚拟的测试数据
MOCK_RECORD = {
    "id": "test_id_123", 
    "date": "2026-11-07", 
    "type": "expense",
    "amount": 10.0, 
    "category": "饮食", 
    "note": "测试备注", 
    "created_at": "2026-11-07T10:00:00+00:00"
}

@patch('storage.save_records')
@patch('storage.load_records')
@patch('models.validate_record')
def test_update_record(mock_validate, mock_load, mock_save):
    """测试修改记录功能"""
    # 模拟从文件读取到数据
    mock_load.return_value = [MOCK_RECORD.copy()]
    
    # 测试 1：修改成功
    updates = {"amount": 20.0, "note": "修改后的备注"}
    assert manage_records.update_record("test_id_123", updates) == True
    mock_save.assert_called_once() # 确保调用了保存
    
    # 测试 2：修改不存在的 ID，返回 False
    assert manage_records.update_record("fake_id", updates) == False
    
    # 测试 3：尝试修改非法字段，应该抛出 ValueError
    with pytest.raises(ValueError):
        manage_records.update_record("test_id_123", {"id": "hacker"})

@patch('storage.save_records')
@patch('storage.load_records')
def test_delete_record(mock_load, mock_save):
    """测试删除记录功能"""
    mock_load.return_value = [MOCK_RECORD.copy()]
    
    # 测试 1：删除成功
    assert manage_records.delete_record("test_id_123") == True
    mock_save.assert_called_once()
    
    # 测试 2：删除不存在的 ID，返回 False
    assert manage_records.delete_record("fake_id") == False