import os
import yaml
from pathlib import Path
from prefect import Flow
from prefect.schedules import CronSchedule
from prefect.tasks.prefect import create_flow_run, wait_for_flow_run
from prefect.run_configs.ecs import ECSRun
from prefect.storage.git import Git
from ooi_harvester.settings.main import harvest_settings

BASE = Path('.').parent.absolute()
CONFIG_PATH = BASE.joinpath(harvest_settings.github.defaults.config_path_str)
RUN_OPTIONS = {
    'env': {
        'PREFECT__CLOUD__HEARTBEAT_MODE': 'thread',
    },
    'cpu': '2 vcpu',
    'memory': '16 GB',
    'labels': ['ecs-agent', 'ooi', 'prod'],
    'task_role_arn': os.environ.get('TASK_ROLE_ARN', None),
    'execution_role_arn': os.environ.get('EXECUTION_ROLE_ARN', None),
    'run_task_kwargs': {
        'cluster': 'prefectECSCluster',
        'launchType': 'FARGATE',
    },
}

project_name = "ooi-harvest"
data_org = "ooi-data"
config_json = yaml.safe_load(CONFIG_PATH.open())
flow_run_name = "-".join(
    [
        config_json['instrument'],
        config_json['stream']['method'],
        config_json['stream']['name'],
    ]
)
schedule = CronSchedule(config_json['workflow_config']['schedule'])
run_config = ECSRun(**RUN_OPTIONS)

# Set the default parent run config image
RUN_OPTIONS.setdefault("image", "cormorack/prefect:0.15.13-python3.8")
parent_run_config = ECSRun(**RUN_OPTIONS)

with Flow(
    flow_run_name, schedule=schedule, run_config=parent_run_config
) as parent_flow:
    flow_run = create_flow_run(
        flow_name="stream_harvest",
        run_name=flow_run_name,
        project_name=project_name,
        parameters={
            'config': config_json,
            'error_test': False,
            'export_da': True,
            'gh_write_da': True,
        },
        run_config=run_config,
    )
    wait_for_flow = wait_for_flow_run(flow_run, raise_final_state=True)  # noqa

parent_flow.storage = Git(
    repo=f"{data_org}/{flow_run_name}",
    flow_path="recipe/flow.py",
    repo_host="github.com",
)
