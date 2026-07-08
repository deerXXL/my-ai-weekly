from web_server import app


if __name__ == "__main__":
    # use_reloader=False 防止后台任务线程被重复启动两次
    app.run(debug=True, use_reloader=False)
