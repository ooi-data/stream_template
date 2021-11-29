import datetime
from github import Github
from ooi_harvester.settings import harvest_settings


def print_rate_limiting_info(gh, user):
    # Compute some info about our GitHub API Rate Limit.
    # Note that it doesn't count against our limit to
    # get this info. So, we should be doing this regularly
    # to better know when it is going to run out. Also,
    # this will help us better understand where we are
    # spending it and how to better optimize it.

    # Get GitHub API Rate Limit usage and total
    gh_api_remaining = gh.get_rate_limit().core.remaining
    gh_api_total = gh.get_rate_limit().core.limit

    # Compute time until GitHub API Rate Limit reset
    gh_api_reset_time = gh.get_rate_limit().core.reset
    gh_api_reset_time -= datetime.utcnow()

    print("")
    print("GitHub API Rate Limit Info:")
    print("---------------------------")
    print("token: ", user)
    print(
        "Currently remaining {remaining} out of {total}.".format(
            remaining=gh_api_remaining, total=gh_api_total
        )
    )
    print("Will reset in {time}.".format(time=gh_api_reset_time))
    print("")
    return gh_api_remaining


def main(dispatch=True):
    gh = Github(harvest_settings.github.pat)
    print_rate_limiting_info(gh, 'GH_PAT')
    data_org = gh.get_organization(harvest_settings.github.data_org)
    for repo in data_org.get_repos():
        if repo.name != 'stream_template':
            try:
                repo.get_contents('config.yaml')
                update_template_wf = next(
                    wf
                    for wf in repo.get_workflows()
                    if wf.name == 'Update from template'
                )
                queued = update_template_wf.get_runs(status='queued').get_page(
                    0
                )
                in_progress = update_template_wf.get_runs(
                    status='in_progress'
                ).get_page(0)
                if len(queued) > 0 or len(in_progress) > 0:
                    print("Skipping workflow run, already in progress")
                else:
                    print(f"Updating template for {repo.name}")
                    if dispatch:
                        update_template_wf.create_dispatch(
                            harvest_settings.github.main_branch
                        )
            except Exception:
                pass


if __name__ == "__main__":
    main()
