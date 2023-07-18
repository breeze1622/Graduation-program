import logging
import re
import random
from db import Database
from flask import Flask, render_template, request, session
from datetime import datetime
import config
from extensions import register_extension, db
from orms import EmployeeORM

app = Flask(__name__)
app.secret_key = 'dhsiamdhpfg284nf7c0wk4nz'
app.config.from_object(config)
register_extension(app)

@app.route('/')
def index_view():
    is_login = session.get('is_login')  #
    if 'is_login' in session and session['is_login']:
        return render_template('index1.html')
    else:
        return render_template('index.html')


@app.route('/register')
def register_view():
    return render_template('register.html')


@app.route('/login')
def login_view():
    return render_template('login.html')

@app.post('/api/send_register_sms')
def send_register_sms():
    # 1. 解析前端传递过来的数据
    data = request.get_json()
    mobile = data['mobile']

    # 2. 校验手机号码
    pattern = r'^1[3-9]\d{9}$'
    ret = re.match(pattern, mobile)
    if not ret:
        return {
            'message': '电话号码不符合格式',
            'code': -1
        }

    # 3. 发送短信验证码，并记录
    session['mobile'] = mobile
    # 3.1 生成随机验证码
    code = random.choices('123456789', k=6)
    session['code'] = ''.join(code)
    logging.warning(''.join(code))
    return {
        'message': '发送短信成功',
        'code': 0
    }


@app.post('/api/register')
def register_api():
    # 1. 解析前端传递过来的数据
    data = request.get_json()
    vercode = data['vercode']
    vercode2 = session['code']
    if vercode != vercode2:
        return {
            'message': '短信验证码错误',
            'code': -1
        }

    nickname = data['nickname']
    mobile = data['mobile']
    password = data['password']
    if not all([nickname, mobile, password]):
        return {
            'message': '数据缺失',
            'code': -1
        }
    Database().insert(nickname, mobile, password)
    return {
        'message': '注册用户成功',
        'code': 0
    }


@app.post('/api/login')
def login_api():
    data = request.get_json()
    ret = Database().search(data['mobile'])
    if not ret:
        return {
            'message': '用户不存在',
            'code': -1
        }
    pwd = ret[0]
    if pwd != data['password']:
        return {
            'message': '用户密码错误',
            'code': -1
        }
    session['is_login'] = True  # 记录用户登录
    return {
        'message': '用户登录成功',
        'code': 0
    }


@app.cli.command()
def create():
    db.drop_all()
    db.create_all()
    from faker import Faker
    import random

    faker = Faker(locale="zh-CN")

    for i in range(100):
        student = EmployeeORM()
        info = faker.simple_profile()
        student.name = info['name']
        student.gender = info['sex']
        student.mobile = faker.phone_number()
        student.address = info['address']
        student.department = random.choice(['售后部门', '前台部门', '技术部门','管理部门'])
        student.save()

@app.route('/api/employee')
def employee_view():
    page = request.args.get('page', type=int, default=1)
    per_page = request.args.get('per_page', type=int, default=10)
    # paginate = EmployeeORM.query.paginate(page=page, per_page=per_page, error_out=False)
    q = db.select(EmployeeORM)
    name = request.args.get('name')
    if name:
        q = q.where(EmployeeORM.name == name)
    paginate = db.paginate(q, page=page, per_page=per_page, error_out=False)
    items: [EmployeeORM] = paginate.items
    return {
        'code': 0,
        'msg': '信息查询成功',
        'count': paginate.total,
        'data': [
            {
                'id': item.id,
                'name': item.name,
                'gender': item.gender,
                'mobile': item.mobile,
                'department': item.department,
                'address': item.address,
                'disable': item.disable,
                'is_del': item.is_del,
                'create_at': item.create_at.strftime('%Y-%m-%d %H:%M:%S'),
                'update_at': item.update_at.strftime('%Y-%m-%d %H:%M:%S'),
            } for item in items
        ]
    }

@app.get('/employee_add')
def employee_add():
    return render_template('employee_add.html')

@app.post('/api/employee')
def api_employee_post():
    data = request.get_json()
    data['create_at'] = datetime.strptime(data['create_at'], '%Y-%m-%d %H:%M:%S')
    employee = EmployeeORM()
    employee.update(data)
    try:
        employee.save()
    except Exception as e:
        return {
            'code': -1,
            'msg': '新增数据失败'
        }
    return {
        'code': 0,
        'msg': '新增数据成功'
    }

@app.put('/api/employee/<int:sid>')
def api_employee_put(sid):
    data = request.get_json()
    data['create_at'] = datetime.strptime(data['create_at'], '%Y-%m-%d %H:%M:%S')
    # employee = EmployeeORM.query.get(sid)
    employee = db.get_or_404(EmployeeORM, sid)
    employee.update(data)
    try:
        employee.save()
    except Exception as e:
        return {
            'code': -1,
            'msg': '修改数据失败'
        }
    return {
        'code': 0,
        'msg': '修改数据成功'
    }

@app.delete('/api/employee/<int:sid>')
def api_employee_del(sid):
    employee: EmployeeORM = db.get_or_404(EmployeeORM, sid)
    try:
        # db.session.delete(employee)
        employee.is_del = True
        db.session.commit()
    except Exception as e:
        return {
            'code': -1,
            'msg': '删除数据失败'
        }
    return {
        'code': 0,
        'msg': '删除数据成功'
    }

@app.put('/api/employee/<int:sid>/department')
def api_employee_department(sid):
    employee: EmployeeORM = db.get_or_404(EmployeeORM, sid)
    data = request.get_json()
    try:
        employee.department = data['department']
        employee.save()
    except Exception as e:
        return {
            'code': -1,
            'msg': '修改班级失败'
        }
    return {
        'code': 0,
        'msg': '修改班级成功'
    }

@app.put('/api/employee/<int:sid>/address')
def api_employee_address(sid):
    employee: EmployeeORM = db.get_or_404(EmployeeORM, sid)
    data = request.get_json()
    try:
        employee.address = data['address']
        employee.save()
    except Exception as e:
        return {
            'code': -1,
            'msg': '修改地址失败'
        }
    return {
        'code': 0,
        'msg': '修改地址成功'
    }

@app.put('/api/employee/<int:sid>/disable')
def api_employee_disable(sid):
    employee: EmployeeORM = db.get_or_404(EmployeeORM, sid)
    data = request.get_json()
    try:
        employee.disable = data['disable']
        employee.save()
    except Exception as e:
        return {
            'code': -1,
            'msg': '修改禁用失败'
        }
    return {
        'code': 0,
        'msg': '修改禁用成功'
    }


if __name__ == '__main__':
    app.run(debug=True)
