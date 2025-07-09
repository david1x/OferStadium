pipeline {
    agent { label 'deepin' }

    environment {
        VENV_DIR = 'venv'
        PYTHON = "${VENV_DIR}/bin/python"
    }

    stages {
        stage('Clone Repo') {
            steps {
                // Clean workspace and clone the repo
                deleteDir()
                git branch: 'main', url: 'https://github.com/david1x/OferStadium.git'
            }
        }
        stage('Setup Python & Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv ${VENV_DIR}
                    . ${VENV_DIR}/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    ${PYTHON} -m playwright install --with-deps
                '''
            }
        }
        stage('Run Script') {
            steps {
                sh '''
                    . ${VENV_DIR}/bin/activate
                    ${PYTHON} main.py
                '''
            }
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'latestGame.png', allowEmptyArchive: true
        }
    }
}