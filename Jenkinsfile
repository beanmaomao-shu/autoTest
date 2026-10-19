// ================================================================
// Jenkins 声明式流水线（Jenkinsfile）
// ----------------------------------------------------------------
// 作用：定义 App 自动化测试在 Jenkins 上的持续集成流程，
// 实现「拉取代码 -> 准备环境 -> 执行用例 -> 生成并展示 allure 报告」的自动化。
//
// 使用前置条件（需在 Jenkins 所在机器/节点提前准备）：
//   1. 安装 Python 3.10+ 并配置到 PATH；
//   2. 安装 Node.js + Appium Server，并安装 uiautomator2 驱动：
//        npm install -g appium
//        appium driver install uiautomator2
//   3. 安装 allure 命令行工具，并在 Jenkins 全局工具中配置 Allure Commandline；
//   4. 安装 Jenkins 插件：Allure Jenkins Plugin（用于展示报告）、
//      Git plugin（拉取代码）；
//   5. 连接好测试设备/模拟器（adb devices 可见）。
// ================================================================
pipeline {
    // agent any 表示在任意可用节点上执行，如有专用移动测试节点可改成 label 'android'
    agent any

    // 全局环境变量
    environment {
        // Python 解释器命令（Windows 上可能是 python，Linux/Mac 上可能是 python3）
        PYTHON = "python"
        // 虚拟环境目录名
        VENV_DIR = "venv"
    }

    // 声明本流水线使用的工具（需与 Jenkins 全局工具配置中的名称一致）
    tools {
        // Allure 命令行工具，名称需与 Jenkins「全局工具配置」里的 Allure Commandline 名称一致
        allure 'allure'
    }

    stages {
        // ---------------- 阶段一：拉取代码 ----------------
        stage('Checkout 拉取代码') {
            steps {
                // 从版本库拉取最新代码；此处使用 SCM（配合 Multibranch/Git 任务）
                checkout scm
                echo '代码拉取完成'
            }
        }

        // ---------------- 阶段二：准备 Python 环境与依赖 ----------------
        stage('Setup 准备环境') {
            steps {
                // 创建虚拟环境（已存在则跳过），并安装 requirements.txt 中的依赖
                // 使用国内镜像源加速下载
                sh '''
                    ${PYTHON} -m venv ${VENV_DIR} || true
                    ./${VENV_DIR}/bin/activate 2>/dev/null || . ${VENV_DIR}/Scripts/activate
                    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
                '''
                echo 'Python 依赖安装完成'
            }
        }

        // ---------------- 阶段三：启动 Appium Server ----------------
        stage('Start Appium Server 启动服务') {
            steps {
                // 后台启动 Appium Server，日志输出到 appium.log
                // --relaxed-security 放开部分权限；端口与 config.yaml 保持一致
                sh 'nohup appium --address 127.0.0.1 --port 4723 --relaxed-security > appium.log 2>&1 &'
                // 等待 Appium Server 完全启动
                sleep(time: 10, unit: 'SECONDS')
                echo 'Appium Server 已启动'
            }
        }

        // ---------------- 阶段四：执行测试用例 ----------------
        stage('Test 执行用例') {
            steps {
                // 激活虚拟环境并运行 pytest，输出 allure 原始结果
                // 即使部分用例失败也让流水线继续（|| true），以便后续生成报告
                sh '''
                    ./${VENV_DIR}/bin/activate 2>/dev/null || . ${VENV_DIR}/Scripts/activate
                    pytest scripts --alluredir=./report/allure-result --clean-alluredir || true
                '''
                echo '测试用例执行完成'
            }
        }
    }

    post {
        always {
            // 无论成功失败，都使用 allure 插件生成并展示测试报告
            // report 指向存放 allure 原始结果 json 的目录
            allure includeProperties: false,
                   results: [[path: 'report/allure-result']]

            // 归档测试日志文件，便于在 Jenkins 上下载排查
            archiveArtifacts artifacts: 'log/*.log', allowEmptyArchive: true, fingerprint: true
        }
        failure {
            // 流水线失败时发送邮件通知（需先在 Jenkins 配置好邮件服务器）
            echo '测试流水线执行失败，请检查 allure 报告与日志！'
            // mail to: 'tester@example.com', subject: 'App 自动化测试失败', body: '请登录 Jenkins 查看详情'
        }
        success {
            echo '测试流水线执行成功！'
        }
        cleanup {
            // 清理：关闭后台启动的 Appium Server 进程，释放设备资源
            sh 'pkill -f appium || true'
            echo '已清理 Appium Server 进程'
        }
    }
}
