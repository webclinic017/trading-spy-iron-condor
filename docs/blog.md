---
layout: page
title: "Blog"
permalink: /blog/
description: "Browse posts by topic. Internal linking hubs for AI trading, options strategy, automation, and lessons learned."
---

# Blog

Browse by topic first (best way to navigate), or scroll recent posts.

---

## Topics

<div class="topic-grid">
  <div class="topic-card">
    <a href="{{ '/topics/ai-trading/' | relative_url }}"><strong>ai-trading</strong></a>
    <div class="topic-count">{{ site.tags['ai-trading'].size | default: 0 }} post(s)</div>
  </div>
  <div class="topic-card">
    <a href="{{ '/topics/lessons-learned/' | relative_url }}"><strong>lessons-learned</strong></a>
    <div class="topic-count">{{ site.tags['lessons-learned'].size | default: 0 }} post(s)</div>
  </div>
  <div class="topic-card">
    <a href="{{ '/topics/options/' | relative_url }}"><strong>options</strong></a>
    <div class="topic-count">{{ site.tags['options'].size | default: 0 }} post(s)</div>
  </div>
  <div class="topic-card">
    <a href="{{ '/topics/iron-condors/' | relative_url }}"><strong>iron-condors</strong></a>
    <div class="topic-count">{{ site.tags['iron-condors'].size | default: 0 }} post(s)</div>
  </div>
  <div class="topic-card">
    <a href="{{ '/topics/rag/' | relative_url }}"><strong>rag</strong></a>
    <div class="topic-count">{{ site.tags['rag'].size | default: 0 }} post(s)</div>
  </div>
  <div class="topic-card">
    <a href="{{ '/topics/automation/' | relative_url }}"><strong>automation</strong></a>
    <div class="topic-count">{{ site.tags['automation'].size | default: 0 }} post(s)</div>
  </div>
</div>

---

## All Tags (A–Z)

{% assign tags_sorted = site.tags | sort %}
<ul>
{% for tag in tags_sorted %}
  {% assign tag_name = tag[0] %}
  {% assign tag_posts = tag[1] %}
  <li>
    <a href="{{ '/topics/' | append: tag_name | append: '/' | relative_url }}">{{ tag_name }}</a>
    <small>({{ tag_posts.size }})</small>
  </li>
{% endfor %}
</ul>

---

## Recent Posts

<ul>
{% for post in site.posts limit: 50 %}
  <li>
    <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
    <small>({{ post.date | date: "%Y-%m-%d" }})</small>
  </li>
{% endfor %}
</ul>

