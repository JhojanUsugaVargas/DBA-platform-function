pipeline {
    agent none

    environment {
        BASE_VERSION = 00
    }

    triggers {
        pollSCM('H/5 * * * *')
    }

    stages {
        stage('Checkout') {
            agent { label 'vbogdtlmosp11' }
            steps {
                echo 'Descargando código del repositorio...'
                checkout scm
            }
        }

        stage('Validate Tools') {
            agent { label 'vbogdtlmosp11' }
            steps {
                sh "sudo -i bash -c 'export PATH=/usr/local/bin:\$PATH; cd ${WORKSPACE} && nerdctl --version'"
            }
        }

        stage('Build Image') {
            agent { label 'vbogdtlmosp11' }
            steps {
                script {
                    def buildNum = env.BUILD_NUMBER.toInteger()
                    env.NEW_VERSION = "v${BASE_VERSION + buildNum}"
                    echo "Construyendo imagen versión: ${env.NEW_VERSION}"
                    
                    sh "sudo -i bash -c 'export PATH=/usr/local/bin:\$PATH; cd ${WORKSPACE} && nerdctl -n k8s.io build -t datacheck-web:${env.NEW_VERSION} -f backend/Dockerfile backend'"
                }
            }
        }

        stage('Prune Old Images') {
            agent { label 'vbogdtlmosp11' }
            steps {
                script {
                    echo "Depurando imágenes antiguas, manteniendo solo las últimas 5..."
                    sh """
                        sudo -i bash -c 'export PATH=/usr/local/bin:\$PATH; \
                        nerdctl -n k8s.io images --format "{{.Tag}}" datacheck-web | \
                        sort -V -r | \
                        tail -n +6 | \
                        xargs -r -I {} nerdctl -n k8s.io rmi datacheck-web:{}'
                    """
                }
            }
        }

        stage('Patch Deployment YAML') {
            agent { label 'vbogdtlmosp11' }
            steps {
                sh "sudo -i bash -c 'export PATH=/usr/local/bin:\$PATH; cd ${WORKSPACE} && sed -i \"s|image: datacheck-web:v.*|image: datacheck-web:${env.NEW_VERSION}|g\" k8s/deployment.yaml'"
                echo "YAML local actualizado con la imagen: ${env.NEW_VERSION}"
            }
        }

        stage('Deploy to K8s') {
            agent { label 'vbogdtlmosp10' }
            steps {
                echo "Iniciando despliegue en el clúster usando el agente vbogdtlmosp10..."
                sh "kubectl set image deployment/datacheck-web datacheck-web=datacheck-web:${env.NEW_VERSION} -n datacheck-web"
                sh "kubectl rollout status deployment/datacheck-web -n datacheck-web"
            }
        }
    }

    post {
        always {
            echo 'Finalizando ejecución del pipeline...'
        }
        success {
            echo "✅ El despliegue de ${env.NEW_VERSION} fue exitoso en el clúster!"
        }
        failure {
            echo '❌ Hubo un error en el pipeline. Revisa los logs.'
        }
    }
}