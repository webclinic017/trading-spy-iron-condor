---
layout: page
title: "Topic: iron-condors"
permalink: /topics/iron-condors/
tag: iron-condors
description: "Iron condor strategy design, trade management, and failure modes."
---

# iron-condors

{% assign tagged = site.tags[page.tag] | default: empty %}
{% if tagged and tagged.size > 0 %}
<ul>
{% for post in tagged %}
  <li>
    <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
    <small>({{ post.date | date: "%Y-%m-%d" }})</small>
  </li>
{% endfor %}
</ul>
{% else %}
No posts found for tag `{{ page.tag }}`.
{% endif %}

