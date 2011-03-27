from zope.interface import implements
from AccessControl import getSecurityManager
from Products.CMFCore.utils import getToolByName
from zope.component import queryAdapter
#from Products.ZCatalog.interfaces import ICatalogBrain how to get this interface???
from Solgema.fullcalendar.browser.solgemafullcalendar_views import getCopyObjectsUID, getColorIndex
from Solgema.fullcalendar.interfaces import *

try:
    from plone.event.interfaces import IRecurrenceSupport
    HAS_RECCURENCE_SUPPORT = True
except ImportError:
    HAS_RECCURENCE_SUPPORT = False


class SolgemaFullcalendarCatalogSearch(object):

    implements(ISolgemaFullcalendarCatalogSearch)

    def __init__(self, context):
        self.context = context

    def searchResults(self, args):
        catalog = getToolByName(self.context, 'portal_catalog')
        return catalog.searchResults(**args)

class SolgemaFullcalendarEditableFilter(object):

    implements(ISolgemaFullcalendarEditableFilter)

    def __init__(self, context):
        self.context = context

    def _listSFAllowedRolesAndUsersModify(self):
        sm = getSecurityManager()
        user = sm.getUser()
        effective_roles = user.getRoles()
        if sm.calledByExecutable():
            eo = sm._context.stack[-1]
            proxy_roles = getattr(eo, '_proxy_roles', None)
            if proxy_roles is not None:
                effective_roles = proxy_roles
        result = list( effective_roles )
        result.append( 'Anonymous' )
        result.append( 'user:%s' % user.getId() )
        return result

    def filterEvents(self, args):
        editargs = args.copy()
        catalog = getToolByName(self.context, 'portal_catalog')
        editargs['SFAllowedRolesAndUsersModify'] = self._listSFAllowedRolesAndUsersModify()
        return [a.getURL() for a in catalog.searchResults(**editargs)]

class SolgemaFullcalendarTopicEventDict(object):

    implements(ISolgemaFullcalendarTopicEventDict)

    def __init__(self, topic, request):
        self.context = topic
        self.request = request
        self.copyDict = getCopyObjectsUID(request)

    def getExtraClass(self, item):
        return ''

    def dictFromBrain(self, brain, args):
        eventsFilter = queryAdapter( self.context, ISolgemaFullcalendarEditableFilter )
        editpaths = eventsFilter.filterEvents(args)
        member = self.context.portal_membership.getAuthenticatedMember()
        memberid = member.id
        if memberid in brain.Creator:
            editable = True
        else:
            editable = False
        if brain.getURL() in editpaths:
            editable = True
        else:
            editable = False
        if brain.end - brain.start > 1.0:
            allday = True
        else:
            allday = False
        if getattr(brain, 'SFAllDay', None) in [False,True]:
            allday = brain.SFAllDay
        copycut = ''
        if self.copyDict and brain.getPath() == self.copyDict['url']:
            copycut = self.copyDict['op'] == 1 and ' event_cutted' or ' event_copied'
        typeClass = ' type-'+brain.portal_type
        colorIndex = getColorIndex(self.context, self.request, brain=brain)
        extraClass = self.getExtraClass(brain)
        if HAS_RECCURENCE_SUPPORT:
            occurences = IRecurrenceSupport(brain.getObject()).occurences()
        else:
            occurences = [{'start_date': brain.start.rfc822(),
                           'end_date': brain.end.rfc822()}]
        events = []
        for occurence in occurences:
            events.append({
                "id": "UID_%s" % (brain.UID),
                "title": brain.Title,
                "description": brain.Description,
                "start": HAS_RECCURENCE_SUPPORT and occurence['start_date'].isoformat() or occurence['start_date'],
                "end": HAS_RECCURENCE_SUPPORT and occurence['end_date'].isoformat() or occurence['end_date'],
                "url": brain.getURL(),
                "editable": editable,
                "allDay": allday,
                "className": "contextualContentMenuEnabled state-" + str(brain.review_state) + (editable and " editable" or "")+copycut+typeClass+colorIndex+extraClass})
        return events

    def dictFromObject(self, item):
        eventPhysicalPath = '/'.join(item.getPhysicalPath())
        wft = getToolByName(self.context, 'portal_workflow')
        state = wft.getInfoFor(self.context, 'review_state')
        member = self.context.portal_membership.getAuthenticatedMember()
        if member.has_permission('Modify portal content', item):
            editable = True
        if item.end() - item.start() > 1.0:
            allday = True
        else:
            allday = False
        adapted = ISFBaseEventFields(item, None)
        if adapted:
            allday = adapted.allDay
        copycut = ''
        if self.copyDict and eventPhysicalPath == self.copyDict['url']:
            copycut = self.copyDict['op'] == 1 and ' event_cutted' or ' event_copied'
        typeClass = ' type-'+item.portal_type
        colorIndex = getColorIndex(self.context, self.request, eventPhysicalPath)
        extraClass = self.getExtraClass(item)
        if HAS_RECCURENCE_SUPPORT:
            occurences = IRecurrenceSupport(event).occurences()
        else:
            occurences = [{'start_date': event.start().rfc822(),
                           'end_date': event.end().rfc822()}]
        events = []
        for occurence in occurences:
            events.append({
                "status": "ok",
                "id": "UID_%s" % (event.UID()),
                "title": event.Title(),
                "description": event.Description(),
                "start": HAS_RECCURENCE_SUPPORT and occurence['start_date'].isoformat() or occurence['start_date'],
                "end": HAS_RECCURENCE_SUPPORT and occurence['end_date'].isoformat() or occurence['end_date'],
                "url": event.absolute_url(),
                "editable": editable,
                "allDay": allday,
                "className": "contextualContentMenuEnabled state-" + str(state) + (editable and " editable" or "")+copycut+typeClass+colorIndex+extraClass})
        return events

    def createDict(self, itemsList=[], args={}):
        li = []
        for item in itemsList:
            if hasattr(item, '_unrestrictedGetObject'):
                li.extend(self.dictFromBrain(item, args))
            else:
                li.extend(self.dictFromObject(item))
        return li

class SolgemaFullcalendarEventDict(object):

    implements(ISolgemaFullcalendarEventDict)

    def __init__(self, event, request):
        self.context = event
        self.request = request
        self.copyDict = getCopyObjectsUID(request)

    def getExtraClass(self):
        return ''

    def __call__(self):
        eventPhysicalPath = '/'.join(self.context.getPhysicalPath())
        wft = getToolByName(self.context, 'portal_workflow')
        state = wft.getInfoFor(self.context, 'review_state')
        member = self.context.portal_membership.getAuthenticatedMember()
        if member.has_permission('Modify portal content', self.context):
            editable = True
        if self.context.end() - self.context.start() > 1.0:
            allday = True
        else:
            allday = False
        adapted = ISFBaseEventFields(self.context, None)
        if adapted:
            allday = adapted.allDay
        copycut = ''
        if self.copyDict and eventPhysicalPath == self.copyDict['url']:
            copycut = self.copyDict['op'] == 1 and ' event_cutted' or ' event_copied'
        typeClass = ' type-'+self.context.portal_type
        colorIndex = getColorIndex(self.context, self.request, eventPhysicalPath)
        extraClass = self.getExtraClass()
        return {"status": "ok",
                "id": "UID_%s" % (self.context.UID()),
                "title": self.context.Title(),
                "description": self.context.Description(),
                "start": self.context.start().rfc822(),
                "end": self.context.end().rfc822(),
                "url": self.context.absolute_url(),
                "editable": editable,
                "allDay": allday,
                "className": "contextualContentMenuEnabled state-" + str(state) + (editable and " editable" or "")+copycut+typeClass+colorIndex+extraClass}

