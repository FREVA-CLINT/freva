"""
.. moduleauthor:: Sebastian Illing

This modules encapsulates all access to databases.
"""

import evaluation_system.model.history.models as hist
import evaluation_system.model.plugins.models as pin

from django.contrib.auth.models import User
from django.db import transaction

from datetime import datetime
import json
import re
import pandas as pd
import socket
from evaluation_system.misc import config
from evaluation_system.model.history.models import Configuration

from evaluation_system.misc import logger as log
import evaluation_system.settings.database

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


def timestamp_to_string(datetime_obj):
    return datetime_obj.strftime(TIMESTAMP_FORMAT)


def timestamp_from_string(date_string):
    """Create a datetime object from a given datetime string."""
    if date_string is None:
        return
    try:
        return pd.Timestamp(date_string).to_pydatetime()
    except:
        raise ValueError("Can't parse a date from '%s'" % date_string)


# class HistoryResultEntry(object):
#     """
#     This class encapsulates the access to the results.
#     """
#     def __init__(self, row):
#         self.id = row[0]
#         self.history_id_id = row[1]
#         self.output_file = row[2]
#         self.preview_file = row[3]
#         self.filetype = row[4]
#
#
# class HistoryTagEntry(object):
#     """
#     This class encapsulates the access to the HistoryTag entries.
#     """
#     def __init__(self, row):
#         self.id = row[0]
#         self.history_id_id = row[1]
#         self.type = row[2]
#         self.uid = row[3]
#         self.text = row[4]


class UserDB(object):
    """Encapsulates access to the local DB of a single user."""

    def __init__(self, user):
        self._user = user

    @transaction.atomic
    @transaction.atomic
    def storeHistory(
        self,
        tool,
        config_dict,
        uid,
        status,
        slurm_output=None,
        result=None,
        flag=None,
        version_details=None,
        caption=None,
    ):
        """Store a an analysis run into the DB.

        :type tool: :class:`evaluation_system.api.plugin.pluginAbstract`
        :param tool: the plugin for which we are storing the information.
        :param config_dict: dictionary with the configuration used for this run,
        :param uid: the user id (useful in a global database)
        :param status: the process status
        :param result: dictionary with the results (created files)."""
        if result is None:
            result = {}
        if slurm_output is None:
            slurm_output = 0
        if flag is None:
            flag = 0
        if version_details is None:
            version_details = 1
        toolname = tool.__class__.__name__.lower()
        version = repr(tool.__version__)
        for key in config.exclude:
            config_dict.pop(key, "")
        newentry = hist.History(
            timestamp=datetime.now(),
            tool=toolname,
            version=version,
            configuration=json.dumps(config_dict),
            slurm_output=slurm_output,
            uid_id=uid,
            status=status,
            flag=flag,
            version_details_id=version_details,
        )
        # set caption
        if caption:
            newentry.caption = caption

        tool.__parameters__.synchronize(toolname)

        try:
            newentry.save()

            for p in tool.__parameters__._params.values():
                if p.name not in config.exclude:
                    name = p.name
                    param = Configuration(
                        history_id_id=newentry.id,
                        parameter_id_id=p.id,
                        value=json.dumps(config_dict[name]),
                        is_default=p.is_default,
                    )
                    param.save()
        except Exception as e:
            raise e

        return newentry.id

    def scheduleEntry(self, row_id, uid, slurmFileName, status=None):
        """Schedule a tool for a future application
        Parameter:
        ----------
        row_id:
            The index in the history table
        uid:
            the user id
        slurmFileName:
            The std out file belonging to the history entry
        stauts:
            Overwrite the default status (scheduled) with this status.
        """

        h = hist.History.objects.get(
            id=row_id, uid_id=uid, status=hist.History.processStatus.not_scheduled
        )

        h.slurm_output = slurmFileName
        h.host = socket.gethostbyname(socket.gethostname())
        h.status = status or hist.History.processStatus.scheduled

        h.save()

    class ExceptionStatusUpgrade(Exception):
        """
        Exception class for failing status upgrades
        """

        def __init__(self, msg="Status could not be upgraded"):
            super(UserDB.ExceptionStatusUpgrade, self).__init__(msg)

    def upgradeStatus(self, row_id, uid, status):
        """
        :param row_id: The index in the history table
        :param uid: the user id
        :param status: the new status
        After validation the status will be upgraded.
        """

        h = hist.History.objects.get(pk=row_id, uid_id=uid)

        if h.status < status:
            raise self.ExceptionStatusUpgrade("Tried to downgrade a status")

        h.status = status

        h.save()

    def changeFlag(self, row_id, uid, flag):
        """
        :param row_id: The index in the history table
        :param uid: the user id
        :param flag: the new flag
        After validation the status will be upgraded.
        """

        h = hist.History.objects.get(id=row_id, uid_id=uid)

        h.flag = flag

        h.save()

    def getHistory(
        self, tool_name=None, limit=-1, since=None, until=None, entry_ids=None, uid=None
    ):
        """Returns the stored history (run analysis) for the given tool.

        :type tool_name: str
        :param tool_name: name of the tool for which the information will be gathered (if None, then everything is returned).
        :type limit: int
        :param limit: Amount of rows to be returned (if < 0, return all).
        :type since: datetime.datetime
        :param since: Return only items stored after this date
        :type until: datetime.datetime
        :param until: Return only  items stored before this date
        :param entry_ids: ([int] or int) id or list thereof to be selected
        :returns: ([:class:`HistoryEntry`]) list of entries that match the query."""
        filter_dict = {}

        if entry_ids is not None:
            if isinstance(entry_ids, int):
                entry_ids = [entry_ids]
            filter_dict["id__in"] = entry_ids

        if tool_name is not None:
            filter_dict["tool"] = tool_name

        if since is not None:
            filter_dict["timestamp__gte"] = since

        if until is not None:
            filter_dict["timestamp__lte"] = until

        if uid is not None:
            filter_dict["uid_id"] = uid

        o = hist.History.objects.filter(**filter_dict).order_by("-id")

        if limit > 0:
            o = o[:limit]

        return o

    def addHistoryTag(self, hrowid, tagType, text, uid=None):
        """
        :type hrowid: integer
        :param hrowid: the row id of the history entry where the results belong to
        :type tagType: integer
        :param tagType: the kind of tag
        :type: text: string
        :param: text: the text belonging to the tag
        :type: uid: string
        :param: uid: the user, default: None
        """

        h = hist.HistoryTag(history_id_id=hrowid, type=tagType, text=text)

        if uid is not None:
            h.uid_id = uid

        h.save()

    def updateHistoryTag(self, trowid, tagType=None, text=None, uid=None):
        """
        :type trowid: integer
        :param trowid: the row id of the tag
        :type tagType: integer
        :param tagType: the kind of tag
        :type: text: string
        :param: text: the text belonging to the tag
        :type: uid: string
        :param: uid: the user, default: None
        """

        h = hist.HistoryTag.objects.get(id=trowid, uid_id=uid)

        if tagType is not None:
            h.type = tagType

        if text is not None:
            h.text = text

        h.save()

    def storeResults(self, rowid, results):
        """
        :type rowid: integer
        :param rowid: the row id of the history entry where the results belong to
        :type results: dict with entries {str : dict}
        :param results: meta-dictionary with meta-data dictionaries assigned to the file names.
        """
        reg_ex = None

        # regex to get the relative path
        preview_path = config.get(config.PREVIEW_PATH, None)
        expression = "(%s\\/*){1}(.*)" % re.escape(preview_path)

        # only try to create previews, when a preview path is given
        if preview_path:
            reg_ex = re.compile(expression)

        for file_name in results:
            metadata = results[file_name]

            type_name = metadata.get("type", "")
            type_number = hist.Result.Filetype.unknown

            preview_path = metadata.get("preview_path", "")
            preview_file = ""

            if preview_path and reg_ex is not None:
                # We store the relative path for previews only.
                # Which allows us to move the preview files to a different folder.
                preview_file = reg_ex.match(preview_path).group(2)

            if type_name == "plot":
                type_number = hist.Result.Filetype.plot
            elif type_name == "data":
                type_number = hist.Result.Filetype.data

            h = hist.Result(
                history_id_id=rowid,
                output_file=file_name,
                preview_file=preview_file,
                file_type=type_number,
            )

            h.save()

            result_id = h.pk
            self._storeResultTags(result_id, metadata)

    def _storeResultTags(self, result_id, metadata):
        """
        :type result_id: integer
        :param result_id: the id of the result entry where the tag belongs to
        :type metadata: dict with entries {str : dict}
        :param metadata: meta-dictionary with meta-data dictionaries assigned to the file names.
        """

        data_to_store = []

        # append new tags here
        caption = metadata.get("caption", None)

        if caption:
            data_to_store.append(
                hist.ResultTag(
                    result_id_id=result_id,
                    type=hist.ResultTag.flagType.caption,
                    text=caption,
                )
            )

        hist.ResultTag.objects.bulk_create(data_to_store)

    def getVersionId(
        self,
        toolname,
        version,
        repos_api,
        internal_version_api,
        repos_tool,
        internal_version_tool,
    ):
        repository = "%s;%s" % (repos_tool, repos_api)

        retval = None

        try:
            p = pin.Version.objects.filter(
                tool=toolname,
                version=version,
                internal_version_tool=internal_version_tool[:40],
                internal_version_api=internal_version_api[:40],
                repository=repository,
            )[0]

            retval = p.pk

        except (IndexError, pin.Version.DoesNotExist) as e:
            pass

        return retval

    def newVersion(
        self,
        toolname,
        version,
        repos_api,
        internal_version_api,
        repos_tool,
        internal_version_tool,
    ):
        repository = "%s;%s" % (repos_tool, repos_api)

        p = pin.Version(
            timestamp=datetime.now(),
            tool=toolname,
            version=version,
            internal_version_tool=internal_version_tool,
            internal_version_api=internal_version_api,
            repository=repository,
        )

        p.save()

        result_id = p.pk

        return result_id

    def getUserId(self, username):
        retval = 0

        try:
            u = User.objects.get(username=username)

            retval = u.pk
        except User.DoesNotExist:
            pass

        return retval

    def updateUserLogin(self, row_id, email=None):
        u = User.objects.get(id=row_id)

        u.last_login = datetime.now()

        if email is not None:
            u.email = email

        u.save()

    def createUser(
        self,
        username,
        email="-",
        first_name="",
        last_name="",
    ):

        timestamp = datetime.now()

        u = User(
            username=username,
            password="NoPasswd",
            date_joined=timestamp,
            last_login=timestamp,
            first_name=first_name,
            last_name=last_name,
            email=email,
            is_active=1,
            is_staff=0,
            is_superuser=0,
        )

        u.save()

    def create_user_crawl(self, crawl_dir, username):
        from evaluation_system.model.solr_models.models import UserCrawl

        crawl = UserCrawl(
            status="waiting", user_id=self.getUserId(username), path_to_crawl=crawl_dir
        )
        crawl.save()
        return crawl.id
