
# Strava

For Strava, both their official API and access via web is used. While their API is required to find existing activities,
download of .gpx and .tcx files can only be done via their website. That's why both web credentials and OAuth
credentials are necessary for Insights to work. It's possible to move to their API only, but then raw data needs to
be transformed into .tcx. This feature might come later.
