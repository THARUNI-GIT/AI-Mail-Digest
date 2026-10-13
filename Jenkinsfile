
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                echo 'Source code is available in the Jenkins workspace.'
            }
        }

        stage('Install Dependencies') {
            steps {
                bat 'python -m pip install -r requirements.txt'
                bat 'python -m pip install pytest selenium'
            }
        }

        stage('Unit Tests') {
            steps {
                bat 'python -m pytest tests -v --junitxml=test-results\\results.xml'
            }
            post {
                always {
                    junit testResults: 'test-results/results.xml',
                          allowEmptyResults: true
                }
            }
        }
    }
}
