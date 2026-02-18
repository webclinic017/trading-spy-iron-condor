---
layout: page
title: "Topic: rag"
permalink: /topics/rag/
tag: rag
description: "Retrieval-augmented generation (RAG), memory, indexing, and evaluation lessons."
---

# rag

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

