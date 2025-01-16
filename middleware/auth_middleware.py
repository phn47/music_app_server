from fastapi import Request, HTTPException
import jwt

async def auth_middleware(request: Request):
    try:
        auth_header = request.headers.get('x-auth-token')
        print("Received token:", auth_header)
        if not auth_header:
            raise HTTPException(status_code=401, detail="Không tìm thấy token")
            
        print("Auth header:", auth_header)
        
        token = auth_header
        
        try:
            payload = jwt.decode(token, 'password_key', algorithms=['HS256'])
            print("Token payload:", payload)
            
            user_id = payload.get('id') or payload.get('uid')
            if not user_id:
                raise HTTPException(status_code=401, detail="Token không hợp lệ")
                
            return {"uid": user_id}
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token đã hết hạn")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Token không hợp lệ")
            
    except Exception as e:
        print("Auth middleware error:", str(e))
        raise HTTPException(status_code=401, detail="Lỗi xác thực")