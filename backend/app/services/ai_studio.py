"""LLM abstraction for Social Media Engineering content."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.core.config import get_settings
from app.models import Brand, BrandGuidelines


PLATFORM_GUIDANCE = {
    "linkedin": {
        "format": "long-form thought leadership",
        "style": "professional, insight-led, concise hashtags",
        "structure": "hook → insight → proof → CTA",
    },
    "instagram": {
        "format": "caption + carousel/reel option",
        "style": "visual-first, conversational, emoji-light",
        "structure": "hook → value bullets → CTA → hashtags",
    },
    "facebook": {
        "format": "community post",
        "style": "warm, shareable, conversational",
        "structure": "story opener → benefit → question CTA",
    },
    "x": {
        "format": "short post / thread starter",
        "style": "compact, punchy, link-friendly",
        "structure": "hook in 1 line → context → CTA",
    },
    "youtube": {
        "format": "title + description + short script",
        "style": "searchable title, scannable description",
        "structure": "title → description chapters → short script",
    },
}


def _brand_context(brand: Brand, guidelines: BrandGuidelines | None) -> dict[str, str]:
    g = guidelines
    return {
        "name": brand.name,
        "description": brand.description or "",
        "website": brand.website or "",
        "tone": brand.tone_of_voice or "clear and practical",
        "audience": brand.target_audience or "business decision makers",
        "products": (g.products_services if g else None) or "",
        "differentiators": (g.differentiators if g else None) or "",
        "keywords": (g.approved_keywords if g else None) or "",
        "restricted": (g.restricted_words if g else None) or "",
        "cta": (g.default_cta if g else None) or "Learn more",
        "visual_style": (g.visual_style if g else None) or "clean modern product photography",
    }


def _slug_tags(topic: str, brand: str, limit: int = 6) -> str:
    words = re.findall(r"[A-Za-z0-9]+", f"{topic} {brand}")
    tags = []
    for w in words:
        t = w.lower()
        if len(t) < 3 or t in tags:
            continue
        tags.append(t)
        if len(tags) >= limit:
            break
    return " ".join(f"#{t}" for t in tags)


def _score(platform: str, body: str) -> dict[str, int]:
    length = len(body or "")
    clarity = 80 if 80 <= length <= 1200 else 65
    platform_fit = {
        "linkedin": 88 if length > 200 else 70,
        "instagram": 86 if length < 1800 else 72,
        "facebook": 84,
        "x": 90 if length <= 280 else 60,
        "youtube": 82,
    }.get(platform, 75)
    return {
        "score_clarity": clarity,
        "score_brand_fit": 78,
        "score_cta": 80,
        "score_platform_fit": platform_fit,
    }


def local_generate(
    brand: Brand,
    guidelines: BrandGuidelines | None,
    topic: str,
    objective: str,
    platforms: list[str],
) -> dict[str, Any]:
    ctx = _brand_context(brand, guidelines)
    master = (
        f"{ctx['name']} campaign concept for “{topic}”. "
        f"Objective: {objective}. Audience: {ctx['audience']}. "
        f"Tone: {ctx['tone']}. Lead with a practical outcome, then platform-specific variants."
    )
    versions = []
    for platform in platforms:
        guide = PLATFORM_GUIDANCE.get(platform, PLATFORM_GUIDANCE["linkedin"])
        if platform == "linkedin":
            body = (
                f"{topic}: what teams actually need to get right.\n\n"
                f"At {ctx['name']}, we see the same pattern: teams jump to tactics before clarifying the outcome.\n\n"
                f"For {ctx['audience']}, the useful move is simple:\n"
                f"1) Define the business goal\n2) Match the message to the channel\n"
                f"3) Measure response, not vanity metrics\n\n"
                f"{ctx['cta']}."
            )
            headline = f"{topic}: a practical playbook for {ctx['audience']}"
            video = None
            image = f"Clean editorial photo representing {topic} for {ctx['name']}, {ctx['visual_style']}"
        elif platform == "instagram":
            body = (
                f"Hook: {topic} doesn’t have to be complicated.\n\n"
                f"Save this if you manage social for {ctx['audience']}.\n\n"
                f"• Start with one clear goal\n• Write channel-native copy\n• Ship, learn, iterate\n\n"
                f"{ctx['cta']} — link in bio."
            )
            headline = f"{topic} in 3 moves"
            video = (
                f"Reel script (30–40s):\n"
                f"0–3s: Bold text “{topic}”\n"
                f"3–15s: Problem for {ctx['audience']}\n"
                f"15–30s: {ctx['name']} approach in 3 beats\n"
                f"30–40s: CTA “{ctx['cta']}”"
            )
            image = f"Carousel cover: bold typography “{topic}”, brand {ctx['name']}, {ctx['visual_style']}"
        elif platform == "facebook":
            body = (
                f"Quick question for anyone working on {topic}:\n\n"
                f"What’s the hardest part right now — planning, creating, or keeping up with replies?\n\n"
                f"{ctx['name']} helps teams keep the whole social lifecycle in one place.\n\n"
                f"{ctx['cta']}."
            )
            headline = f"Let’s talk about {topic}"
            video = None
            image = f"Friendly community visual about {topic}, brand {ctx['name']}"
        elif platform == "x":
            body = (
                f"{topic} tip: stop copying one generic post everywhere.\n"
                f"Write once for the idea, then adapt for each channel.\n"
                f"{ctx['cta']} → {ctx['website'] or ctx['name']}"
            )[:280]
            headline = topic
            video = None
            image = f"Minimal card graphic: {topic}"
        else:  # youtube
            body = (
                f"In this video we break down {topic} for {ctx['audience']}.\n\n"
                f"Chapters:\n00:00 Why {topic} matters\n"
                f"00:45 Common mistakes\n01:30 A better workflow\n"
                f"02:30 How {ctx['name']} approaches it\n03:15 Next step\n\n"
                f"{ctx['cta']}."
            )
            headline = f"{topic}: what {ctx['audience']} should do this week"
            video = (
                f"Short/Video script:\n"
                f"Hook: “{topic} is broken for most teams.”\n"
                f"Problem → Framework → {ctx['name']} example → CTA."
            )
            image = f"YouTube thumbnail: high-contrast text “{topic}”, face/product optional, {ctx['visual_style']}"

        scores = _score(platform, body)
        versions.append(
            {
                "platform": platform,
                "format": guide["format"],
                "headline": headline,
                "body": body,
                "hashtags": _slug_tags(topic, ctx["name"]),
                "cta": ctx["cta"],
                "image_prompt": image,
                "video_script": video,
                **scores,
            }
        )
    return {
        "master_concept": master,
        "title": topic[:120] if topic else f"{ctx['name']} campaign",
        "objective": objective,
        "versions": versions,
        "provider": "local",
    }


def local_ideas(brand: Brand, guidelines: BrandGuidelines | None, count: int = 5) -> list[dict[str, Any]]:
    ctx = _brand_context(brand, guidelines)
    seeds = [
        (f"3 mistakes {ctx['audience']} make with social publishing", "carousel", "education", "linkedin,instagram", "high"),
        (f"How {ctx['name']} turns one idea into 5 platform posts", "reel", "product", "instagram,youtube", "high"),
        (f"A weekly content system for {ctx['audience']}", "long-form", "thought-leadership", "linkedin", "medium"),
        (f"Before/after: chaotic social ops vs engineered workflow", "carousel", "awareness", "instagram,facebook", "medium"),
        (f"Ask us anything: {ctx['name']} social engineering tips", "community", "engagement", "facebook,x", "medium"),
        (f"What to measure beyond likes for {topic_safe(ctx)}", "thread", "education", "x,linkedin", "medium"),
    ]
    out = []
    for title, fmt, goal, platforms, confidence in seeds[:count]:
        out.append(
            {
                "title": title,
                "format": fmt,
                "goal": goal,
                "platforms": platforms,
                "confidence": confidence,
                "rationale": f"Aligned to {ctx['name']} tone ({ctx['tone']}) and audience ({ctx['audience']}).",
            }
        )
    return out


def topic_safe(ctx: dict[str, str]) -> str:
    return ctx.get("products") or ctx.get("name") or "growth teams"


def local_rewrite(text: str, platform: str, instruction: str, brand: Brand) -> dict[str, Any]:
    ctx = _brand_context(brand, None)
    rewritten = (
        f"{text.strip()}\n\n"
        f"— Reworked for {platform}: {instruction or 'tighter hook and clearer CTA'}. "
        f"Keep {ctx['name']} voice ({ctx['tone']}). {ctx['cta']}."
    )
    if platform == "x":
        rewritten = rewritten[:280]
    return {"body": rewritten, "provider": "local", **_score(platform, rewritten)}


async def openai_chat(messages: list[dict[str, str]], model: str | None = None) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    payload = {
        "model": model or settings.openai_model,
        "messages": messages,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        res.raise_for_status()
        data = res.json()
        return data["choices"][0]["message"]["content"]


async def generate_content(
    brand: Brand,
    guidelines: BrandGuidelines | None,
    topic: str,
    objective: str,
    platforms: list[str],
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openai_api_key:
        return local_generate(brand, guidelines, topic, objective, platforms)

    ctx = _brand_context(brand, guidelines)
    prompt = {
        "brand": ctx,
        "topic": topic,
        "objective": objective,
        "platforms": platforms,
        "instructions": (
            "Act as a Social Media Engineer. Return JSON with keys: "
            "title, master_concept, objective, versions[]. "
            "Each version needs platform, format, headline, body, hashtags, cta, "
            "image_prompt, video_script (nullable), score_clarity, score_brand_fit, "
            "score_cta, score_platform_fit (0-100 ints)."
        ),
    }
    try:
        raw = await openai_chat(
            [
                {"role": "system", "content": "You are Fingers Social Media Engineer. Reply with JSON only."},
                {"role": "user", "content": json.dumps(prompt)},
            ]
        )
        data = json.loads(raw)
        data["provider"] = "openai"
        if "versions" not in data:
            raise ValueError("missing versions")
        return data
    except Exception:
        fallback = local_generate(brand, guidelines, topic, objective, platforms)
        fallback["provider"] = "local_fallback"
        return fallback


async def generate_ideas(brand: Brand, guidelines: BrandGuidelines | None, count: int = 5) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openai_api_key:
        return {"ideas": local_ideas(brand, guidelines, count), "provider": "local"}
    ctx = _brand_context(brand, guidelines)
    try:
        raw = await openai_chat(
            [
                {
                    "role": "system",
                    "content": "Return JSON {ideas:[{title,format,goal,platforms,confidence,rationale}]}",
                },
                {
                    "role": "user",
                    "content": json.dumps({"brand": ctx, "count": count}),
                },
            ]
        )
        data = json.loads(raw)
        data["provider"] = "openai"
        return data
    except Exception:
        return {"ideas": local_ideas(brand, guidelines, count), "provider": "local_fallback"}


async def rewrite_content(
    text: str,
    platform: str,
    instruction: str,
    brand: Brand,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openai_api_key:
        return local_rewrite(text, platform, instruction, brand)
    try:
        raw = await openai_chat(
            [
                {"role": "system", "content": "Return JSON {body, score_clarity, score_brand_fit, score_cta, score_platform_fit}"},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "text": text,
                            "platform": platform,
                            "instruction": instruction,
                            "brand": brand.name,
                            "tone": brand.tone_of_voice,
                        }
                    ),
                },
            ]
        )
        data = json.loads(raw)
        data["provider"] = "openai"
        return data
    except Exception:
        out = local_rewrite(text, platform, instruction, brand)
        out["provider"] = "local_fallback"
        return out
