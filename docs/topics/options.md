---
layout: page
title: "Topic: options"
permalink: /topics/options/
tag: options
description: "Options mechanics, execution, risk, and strategy notes used by the system."
---

# options

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

