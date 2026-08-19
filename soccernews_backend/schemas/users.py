"""用户模块数据验证模型"""
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


#   2.定义数据校验模型类
class UserRegister(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=50, description="密码")


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserUpdate(BaseModel):
    """更新用户信息请求（均为可选）"""
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    gender: Optional[str] = Field(None, description="性别")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")


class PasswordUpdate(BaseModel):
    """修改密码请求"""
    oldPassword: str = Field(..., description="当前密码")
    newPassword: str = Field(..., min_length=6, description="新密码")


# user_info 对应的类：基础类 + info类（用户基础信息）
class UserInFoBase(BaseModel):
    # 用户信息基础数据模型
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    gender: Optional[str] = Field(None, description="性别")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")


class UserInFoResponse(UserInFoBase):
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")

    # 模型配置
    model_config = ConfigDict(
        from_attributes=True  # 允许从ORM对象（SQLAlchemy 模型）属性中取值
    )


# data数据类型
class UserAuthResponse(BaseModel):
    token: str = Field(..., description="令牌值")
    userInfo: UserInFoResponse = Field(..., description="用户信息")




