import json
import logging

from django.contrib.auth.decorators import login_required
from django.db import connection

from seqr.views.auth_api import API_LOGIN_REQUIRED_URL
from seqr.views.utils import \
    _get_json_for_user, \
    render_with_initial_json, \
    create_json_response
from seqr.models import Project

logger = logging.getLogger(__name__)


@login_required
def dashboard_page(request):
    """Generates the dashboard page, with initial dashboard_page_data json embedded."""

    initial_json = json.loads(
        dashboard_page_data(request).content
    )

    return render_with_initial_json('dashboard.html', initial_json)


@login_required(login_url=API_LOGIN_REQUIRED_URL)
def dashboard_page_data(request):
    """Returns a JSON object containing information used by the case review page:
    ::

      json_response = {
         'user': {..},
         'familiesByGuid': {..},
         'individualsByGuid': {..},
         'familyGuidToIndivGuids': {..},
       }
    Args:
        project_guid (string): GUID of the Project under case review.
    """

    # get all projects this user has permissions to view
    if request.user.is_staff:
        projects = projects_user_can_edit = Project.objects.all()
        projects_WHERE_clause = ''
    else:
        projects = Project.objects.filter(can_view_group__user=request.user)
        projects_WHERE_clause = 'WHERE p.guid in (%s)' % (','.join("'%s'" % p.guid for p in projects))
        projects_user_can_edit = Project.objects.filter(can_edit_group__user=request.user)

    # use raw SQL to avoid making N+1 queries.

    num_families_subquery = """
      SELECT count(*) FROM seqr_family
        WHERE project_id=p.id
    """.strip()

    num_individuals_subquery = """
      SELECT count(*) FROM seqr_individual AS i
        JOIN seqr_family AS f on i.family_id=f.id
        WHERE f.project_id=p.id
    """.strip()

    projects_query = """
      SELECT
        guid AS project_guid,
        project_category,
        p.name AS name,
        description,
        deprecated_project_id,
        created_date,
        (%(num_families_subquery)s) AS num_families,
        (%(num_individuals_subquery)s) AS num_individuals
      FROM seqr_project AS p
      %(projects_WHERE_clause)s
    """.strip() % locals()

    cursor = connection.cursor()
    cursor.execute(projects_query)

    columns = [_to_camel_case(col[0]) for col in cursor.description]

    projects_by_guid = {
        r['projectGuid']: r for r in (dict(zip(columns, row)) for row in cursor.fetchall())
    }


    # do a separate query to get details on all datasets in these projects
    num_samples_subquery = """
      SELECT COUNT(*) FROM seqr_sequencingsample AS subquery_s
        WHERE subquery_s.dataset_id=d.id
    """
    datasets_query = """
        SELECT
          p.guid AS project_guid,
          d.sequencing_type AS sequencing_type,
          d.is_loaded AS is_loaded,
          (%(num_samples_subquery)s) AS num_samples
        FROM seqr_dataset AS d
          JOIN seqr_sequencingsample AS s ON d.id=s.dataset_id
          JOIN seqr_individual_sequencing_samples AS iss ON iss.sequencingsample_id=s.id
          JOIN seqr_individual AS i ON iss.individual_id=i.id
          JOIN seqr_family AS f ON i.family_id=f.id
          JOIN seqr_project AS p ON f.project_id=p.id %(projects_WHERE_clause)s
        GROUP BY p.guid, d.id, d.sequencing_type, d.is_loaded
    """.strip() % locals()

    cursor.execute(datasets_query)
    columns = [_to_camel_case(col[0]) for col in cursor.description]
    for row in cursor.fetchall():
        dataset_record = dict(zip(columns, row))
        dataset_project_guid = dataset_record['projectGuid']
        del dataset_record['projectGuid']
        project_record = projects_by_guid[dataset_project_guid]
        if 'datasets' not in project_record:
            project_record['datasets'] = [dataset_record]
        else:
            project_record['datasets'].append(dataset_record)

    cursor.close()

    # mark all projects where this user has edit permissions
    for project in projects_user_can_edit:
        projects_by_guid[project.guid]['canEdit'] = True

    json_response = {
        'user': _get_json_for_user(request.user),
        'projectsByGuid': projects_by_guid,
    }

    return create_json_response(json_response)


def _to_camel_case(snake_case_str):
    components = snake_case_str.split('_')
    return components[0] + "".join(x.title() for x in components[1:])