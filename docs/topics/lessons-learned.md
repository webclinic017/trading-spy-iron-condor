---
layout: page
title: "Topic: lessons-learned"
permalink: /topics/lessons-learned/
tag: lessons-learned
description: "Daily lessons learned from building and operating the AI trading system."
---

# lessons-learned

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

