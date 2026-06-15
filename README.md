# Telegram AI Learning Bot

A production-ready, context-aware Telegram learning bot designed to deliver personalized educational experiences. Built using **LangGraph** and **LangChain** for advanced state management, powered by **Groq** cloud LLMs, backed by **Supabase** for persistent user-state tracking, and deployed via **Render**.

---

## 🚀 Overview

This project is an interactive learning assistant engineered for Telegram. Unlike simple request-response bots, this application leverages graph-based orchestration to manage multi-turn educational workflows, remember user progress, and dynamically adapt to individual learning paces. 

---

## 🛠️ Tech Stack & Architecture

* **Orchestration & Frameworks:** LangGraph, LangChain (Python)
* **Large Language Model:** Groq Cloud API (High-performance, low-latency LLM inference)
* **Database & Persistence:** Supabase (PostgreSQL) for session management and user data storage
* **Deployment:** Render (Web Service architecture)
* **Interface:** Telegram Bot API

---

## ✨ Key Features

* **Stateful Learning Paths:** Uses LangGraph to manage complex, non-linear educational conversations and track user context across multiple sessions.
* **Ultra-Low Latency Responses:** Integrated with Groq’s hardware-accelerated LLM API to provide near-instantaneous explanations and answers.
* **Persistent User Memory:** Seamlessly stores user profiles, interaction history, and progress metrics in Supabase, ensuring continuity even after bot restarts.
* **Production Deployment:** Fully configured for seamless, continuous deployment on Render with robust environment variable handling.

---

## 🏗️ System Architecture

```text
[ Telegram User ] <---> [ Telegram API ] <---> [ Python App (Render) ]
                                                       |
                                        +--------------+--------------+
                                        |                             |
                                 [ LangGraph ]                 [ Supabase DB ]
                        (State & Conversation Flow)         (Session & User Logs)
                                        |
                                  [ LangChain ]
                                        |
                                [ Groq LLM API ]

Prerequisites
-Python 3.10+
-A Telegram Bot Token (from @BotFather)
-A Groq API Key
-A Supabase Project (URL and Service Role Key)

Installation & Local Setup
Clone the repository:
git clone [https://github.com/your-username/telegram-learning-bot.git](https://github.com/Riyajangid123/telegram-learning-bot.git)
cd telegram-learning-bot

Contact & Connect
GitHub: Riyajangid123
LinkedIn: www.linkedin.com/in/riya-jangid
