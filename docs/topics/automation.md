---
layout: page
title: "Topic: automation"
permalink: /topics/automation/
tag: automation
description: "Automation across CI, Ralph Mode, and operational workflows."
---

# automation

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

