"""
Deploy command for FastAPI Microservices SDK CLI.
"""

import os
import subprocess
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from ...deploy.docker.dockerfile_generator import DockerfileGenerator
from ...deploy.docker.compose_generator import ComposeGenerator
from ...deploy.kubernetes.manifest_generator import ManifestGenerator
from ...utils.validators import validate_service_name

console = Console()
deploy_app = typer.Typer(name="deploy", help="Deploy services to different environments")


@deploy_app.command("docker")
def deploy_docker(
    service_path: str = typer.Argument(".", help="Path to service directory"),
    build: bool = typer.Option(True, help="Build Docker image"),
    run: bool = typer.Option(False, help="Run container after build"),
    tag: Optional[str] = typer.Option(None, help="Docker image tag"),
    port: Optional[int] = typer.Option(None, help="Port to expose"),
    env_file: Optional[str] = typer.Option(None, help="Environment file to use")
):
    """Deploy service using Docker."""
    
    service_path = Path(service_path).resolve()
    
    if not service_path.exists():
        rprint(f"❌ [red]Service directory '{service_path}' not found[/red]")
        raise typer.Exit(1)
    
    # Get service name from directory or config
    service_name = _get_service_name(service_path)
    if not service_name:
        rprint("❌ [red]Could not determine service name[/red]")
        raise typer.Exit(1)
    
    # Generate Dockerfile if it doesn't exist
    dockerfile_path = service_path / "Dockerfile"
    if not dockerfile_path.exists():
        rprint("📝 [yellow]Generating Dockerfile...[/yellow]")
        _generate_dockerfile(service_path, service_name)
    
    # Build Docker image
    if build:
        image_tag = tag or f"{service_name}:latest"
        rprint(f"🔨 [blue]Building Docker image: {image_tag}[/blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Building image...", total=None)
            
            try:
                result = subprocess.run([
                    "docker", "build", "-t", image_tag, str(service_path)
                ], capture_output=True, text=True, cwd=service_path)
                
                if result.returncode != 0:
                    rprint(f"❌ [red]Docker build failed:[/red]")
                    rprint(result.stderr)
                    raise typer.Exit(1)
                
                progress.update(task, completed=True)
                rprint(f"✅ [green]Successfully built image: {image_tag}[/green]")
                
            except FileNotFoundError:
                rprint("❌ [red]Docker not found. Please install Docker first.[/red]")
                raise typer.Exit(1)
    
    # Run container
    if run:
        container_port = port or 8000
        image_tag = tag or f"{service_name}:latest"
        
        docker_cmd = [
            "docker", "run", "-d",
            "-p", f"{container_port}:{container_port}",
            "--name", f"{service_name}-container"
        ]
        
        if env_file:
            docker_cmd.extend(["--env-file", env_file])
        
        docker_cmd.append(image_tag)
        
        rprint(f"🚀 [blue]Starting container on port {container_port}...[/blue]")
        
        try:
            result = subprocess.run(docker_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                if "already in use" in result.stderr:
                    rprint(f"⚠️  [yellow]Container name already in use. Stopping existing container...[/yellow]")
                    subprocess.run(["docker", "stop", f"{service_name}-container"], capture_output=True)
                    subprocess.run(["docker", "rm", f"{service_name}-container"], capture_output=True)
                    
                    # Retry
                    result = subprocess.run(docker_cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    rprint(f"❌ [red]Failed to start container:[/red]")
                    rprint(result.stderr)
                    raise typer.Exit(1)
            
            container_id = result.stdout.strip()
            rprint(f"✅ [green]Container started successfully![/green]")
            rprint(f"🔗 Container ID: {container_id[:12]}")
            rprint(f"🌐 Service available at: http://localhost:{container_port}")
            rprint(f"📋 View logs: docker logs {service_name}-container")
            rprint(f"🛑 Stop container: docker stop {service_name}-container")
            
        except FileNotFoundError:
            rprint("❌ [red]Docker not found. Please install Docker first.[/red]")
            raise typer.Exit(1)


@deploy_app.command("compose")
def deploy_compose(
    service_path: str = typer.Argument(".", help="Path to service directory"),
    generate: bool = typer.Option(True, help="Generate docker-compose.yml"),
    up: bool = typer.Option(False, help="Start services with docker-compose up"),
    detach: bool = typer.Option(True, help="Run in detached mode")
):
    """Deploy service using Docker Compose."""
    
    service_path = Path(service_path).resolve()
    
    if not service_path.exists():
        rprint(f"❌ [red]Service directory '{service_path}' not found[/red]")
        raise typer.Exit(1)
    
    service_name = _get_service_name(service_path)
    
    # Generate docker-compose.yml if needed
    compose_file = service_path / "docker-compose.yml"
    if generate or not compose_file.exists():
        rprint("📝 [yellow]Generating docker-compose.yml...[/yellow]")
        _generate_compose_file(service_path, service_name)
    
    # Start services
    if up:
        rprint("🚀 [blue]Starting services with Docker Compose...[/blue]")
        
        compose_cmd = ["docker-compose", "up"]
        if detach:
            compose_cmd.append("-d")
        
        try:
            result = subprocess.run(compose_cmd, cwd=service_path)
            
            if result.returncode == 0:
                rprint("✅ [green]Services started successfully![/green]")
                if detach:
                    rprint("📋 View logs: docker-compose logs -f")
                    rprint("🛑 Stop services: docker-compose down")
            else:
                rprint("❌ [red]Failed to start services[/red]")
                raise typer.Exit(1)
                
        except FileNotFoundError:
            rprint("❌ [red]Docker Compose not found. Please install Docker Compose first.[/red]")
            raise typer.Exit(1)


@deploy_app.command("kubernetes")
def deploy_kubernetes(
    service_path: str = typer.Argument(".", help="Path to service directory"),
    namespace: str = typer.Option("default", help="Kubernetes namespace"),
    generate: bool = typer.Option(True, help="Generate Kubernetes manifests"),
    apply: bool = typer.Option(False, help="Apply manifests to cluster"),
    dry_run: bool = typer.Option(False, help="Perform a dry run")
):
    """Deploy service to Kubernetes."""
    
    service_path = Path(service_path).resolve()
    
    if not service_path.exists():
        rprint(f"❌ [red]Service directory '{service_path}' not found[/red]")
        raise typer.Exit(1)
    
    service_name = _get_service_name(service_path)
    
    # Generate Kubernetes manifests
    if generate:
        rprint("📝 [yellow]Generating Kubernetes manifests...[/yellow]")
        _generate_k8s_manifests(service_path, service_name, namespace)
    
    # Apply manifests
    if apply:
        manifests_dir = service_path / "k8s"
        if not manifests_dir.exists():
            rprint("❌ [red]No Kubernetes manifests found. Run with --generate first.[/red]")
            raise typer.Exit(1)
        
        rprint(f"🚀 [blue]Deploying to Kubernetes namespace: {namespace}[/blue]")
        
        kubectl_cmd = ["kubectl", "apply", "-f", str(manifests_dir)]
        if dry_run:
            kubectl_cmd.append("--dry-run=client")
        
        try:
            result = subprocess.run(kubectl_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                if dry_run:
                    rprint("✅ [green]Dry run successful! Manifests are valid.[/green]")
                else:
                    rprint("✅ [green]Successfully deployed to Kubernetes![/green]")
                    rprint(f"📋 Check status: kubectl get pods -n {namespace}")
                    rprint(f"📋 View logs: kubectl logs -f deployment/{service_name} -n {namespace}")
            else:
                rprint("❌ [red]Kubernetes deployment failed:[/red]")
                rprint(result.stderr)
                raise typer.Exit(1)
                
        except FileNotFoundError:
            rprint("❌ [red]kubectl not found. Please install kubectl first.[/red]")
            raise typer.Exit(1)


@deploy_app.command("local")
def deploy_local(
    service_path: str = typer.Argument(".", help="Path to service directory"),
    port: int = typer.Option(8000, help="Port to run service on"),
    reload: bool = typer.Option(True, help="Enable auto-reload"),
    env_file: Optional[str] = typer.Option(None, help="Environment file to use")
):
    """Deploy service locally for development."""
    
    service_path = Path(service_path).resolve()
    
    if not service_path.exists():
        rprint(f"❌ [red]Service directory '{service_path}' not found[/red]")
        raise typer.Exit(1)
    
    # Check for main.py
    main_file = service_path / "main.py"
    if not main_file.exists():
        rprint("❌ [red]main.py not found in service directory[/red]")
        raise typer.Exit(1)
    
    # Load environment variables
    if env_file:
        env_path = service_path / env_file
        if env_path.exists():
            rprint(f"📋 [blue]Loading environment from: {env_file}[/blue]")
            _load_env_file(env_path)
    
    # Start service
    rprint(f"🚀 [blue]Starting service locally on port {port}...[/blue]")
    rprint(f"🌐 Service will be available at: http://localhost:{port}")
    rprint(f"📋 Press Ctrl+C to stop the service")
    
    try:
        import uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            reload=reload,
            app_dir=str(service_path)
        )
    except ImportError:
        rprint("❌ [red]uvicorn not found. Installing...[/red]")
        subprocess.run(["pip", "install", "uvicorn[standard]"])
        import uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            reload=reload,
            app_dir=str(service_path)
        )
    except KeyboardInterrupt:
        rprint("\n🛑 [yellow]Service stopped by user[/yellow]")


def _get_service_name(service_path: Path) -> Optional[str]:
    """Extract service name from directory or config."""
    
    # Try to get from directory name
    service_name = service_path.name
    if validate_service_name(service_name):
        return service_name
    
    # Try to get from config files
    config_files = [".env", "config.yml", "config.yaml"]
    for config_file in config_files:
        config_path = service_path / config_file
        if config_path.exists():
            try:
                if config_file.endswith(('.yml', '.yaml')):
                    with open(config_path) as f:
                        config = yaml.safe_load(f)
                        if isinstance(config, dict) and 'service_name' in config:
                            return config['service_name']
                else:
                    # Parse .env file
                    with open(config_path) as f:
                        for line in f:
                            if line.startswith('SERVICE_NAME='):
                                return line.split('=', 1)[1].strip()
            except Exception:
                continue
    
    return service_path.name


def _generate_dockerfile(service_path: Path, service_name: str):
    """Generate Dockerfile for the service."""
    try:
        generator = DockerfileGenerator()
        dockerfile_content = generator.generate(service_name, service_path)
        
        dockerfile_path = service_path / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)
        
        rprint(f"✅ [green]Generated Dockerfile at: {dockerfile_path}[/green]")
    except Exception as e:
        rprint(f"❌ [red]Failed to generate Dockerfile: {e}[/red]")
        raise typer.Exit(1)


def _generate_compose_file(service_path: Path, service_name: str):
    """Generate docker-compose.yml for the service."""
    try:
        generator = ComposeGenerator()
        compose_content = generator.generate(service_name, service_path)
        
        compose_path = service_path / "docker-compose.yml"
        compose_path.write_text(compose_content)
        
        rprint(f"✅ [green]Generated docker-compose.yml at: {compose_path}[/green]")
    except Exception as e:
        rprint(f"❌ [red]Failed to generate docker-compose.yml: {e}[/red]")
        raise typer.Exit(1)


def _generate_k8s_manifests(service_path: Path, service_name: str, namespace: str):
    """Generate Kubernetes manifests for the service."""
    try:
        generator = ManifestGenerator()
        manifests = generator.generate(service_name, service_path, namespace)
        
        k8s_dir = service_path / "k8s"
        k8s_dir.mkdir(exist_ok=True)
        
        for filename, content in manifests.items():
            manifest_path = k8s_dir / filename
            manifest_path.write_text(content)
        
        rprint(f"✅ [green]Generated Kubernetes manifests in: {k8s_dir}[/green]")
        rprint(f"📁 Generated files: {', '.join(manifests.keys())}")
    except Exception as e:
        rprint(f"❌ [red]Failed to generate Kubernetes manifests: {e}[/red]")
        raise typer.Exit(1)


def _load_env_file(env_path: Path):
    """Load environment variables from file."""
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    except Exception as e:
        rprint(f"⚠️  [yellow]Warning: Could not load env file: {e}[/yellow]")


if __name__ == "__main__":
    deploy_app()