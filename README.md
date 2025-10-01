# TL;DR

Uses data from [taskwarrior](https://taskwarrior.org/) and [timewarrior](https://timewarrior.net/) to indicate which task should be done next considering both its urgency and the time already spent on it. Its logic is inspired on the [Linux CFS scheduler](https://docs.kernel.org/scheduler/sched-design-CFS.html).

# Installation

## Dependencies

The following dependencies are not python dependencies and must be installed through your system's package manager

* [Taskwarrior](https://taskwarrior.org/)
* [Timewarrior](https://timewarrior.net/)
* [Hook for linking Taskwarrior to Timewarrior](https://timewarrior.net/docs/taskwarrior/)

## Install with pip

It is possible to install via pip by:

```
pip install taskwarrior-scheduler
```

# How to use it

1. Run ``next`` to know on what task you should focus next
2. Log the task you are doing to timewarrior (preferably via a [taskwarrior hook](https://timewarrior.net/docs/taskwarrior/))
3. When you feel you are not performing as you should, or when you feel reached an important milestone, or when the task is too dull to be handled, hit ``next`` and check if there is another task you could focus on.
4. Stop the time tracking whenever you stop working

## Hints 

1. Do not change tasks when you feel you are being productive, even if the task you are working on isn't the most urgent;
2. Learn to do "partial breaks" by [filtering tasks] (https://taskwarrior.org/docs/filter/) (yes, I am talking about the ``-work`` during office hours). The script will know how to balance back when you stop this partial break;
2. Define clear criteria for when you should be working on tasks and when you should be taking breaks or partial breaks;
3. Learn to distinguish between the times when you need a little push to get things done, when you need a partial break, when you need a full break and when you need to sleep.

# How does it work

## Introduction

Taskwarrior is meant to be used to organize tasks according to their urgencies, so that the user can dedicate always to complete the most urgent task. However, sometimes the most urgent task is too complex and takes a lot of time and effort to be completed.

The [best practices](https://taskwarrior.org/docs/best-practices/) state that, in this case, a complex task should be broken into smaller units of work, so that the user has the opportunity to plan ahead. This is a sensible advice, but users are humans. And humans are not always in the best state of mind to realize they are getting stuck in a task that should be better planned, specially if they are too focused on getting it done as soon as possible.

My story in that matter started by the second half of 2024, when I had to get my master thesis done in (what seemed to me was) a very short time. I was stuck in a chapter and no matter the strategy, I was simply stuck. I tried breaking into smaller tasks but it didn't work because I got stuck into every related task, no regardless how small it was. Pomodoro timer just got me more anxious when I realized I couldn't perform as well as I thought I should in that time. And taking a break just to take my head out of things was the worst of it all, because I simply wouldn't get back to work. The worst part of it all was that I didn't have the time to fully dedicate to my thesis, I had other tasks too, including several projects at my job, which I was deliberately delaying in order to get my thesis done --- after all, my Thesis had the greatest urgency in taskwarrior. I was a mess.

I felt like a (old?) Windows, frequently freezing while executing a demanding thread. And ironically it was the spark I needed to create a method (which comes down to this script) to organize my time so I wouldn't to get stuck in a time-consuming task as well as not neglecting important tasks. The rationale is:

1. All tasks must have a fraction of your time that must be related to its urgency. More urgent times must have a greater share.
1. The task to be done next must be the one whose *time spent* fraction is the most distance from the ideal fraction, calculated considering its urgency

As a result, the most urgent tasks will have the greatest shares of the time, but there will be a rotation of tasks to less urgent tasks.

## Ideal time calculation

The timeshare for a task with urgency *u* in a set *Us* of tasks is given by:

![equation](https://latex.codecogs.com/svg.image?\frac{e^{u_j}}{\sum_{u_i\in&space;U_s}{e^{u_i}}}\cdot \Phi_j)

Where ![equation](https://latex.codecogs.com/svg.image?\Phi_j) is the tag/project correction coefficient.

This equation has two important properties:

1. The timeshare will only be affected by the difference of urgency not by the absolute value of this urgency
2. When a task is removed from the set (if it was done or filtered out), its timeshare will be proportionately taken by the other tasks, according to their urgencies.

## Next task selection

The next task will be chosen according to the expression:

![equation](https://latex.codecogs.com/svg.image?\max_{j\in&space;S}\left\{\frac{e^{u_j}}{\sum_{u_i\in&space;U_s}{e^{u_i}}}\cdot \Phi_j-\frac{t_j}{\sum_{t_i\in&space;T_s}{t_i}}\right\})

Where t is the time already spent on which task. In a nutshell, this expressions selects the task whose *time spent* fraction is the most distance from the ideal fraction.

## Tag/project correction coefficient

Time spent on completed or filtered out tasks are considered by the ![equation](https://latex.codecogs.com/svg.image?\Phi_j) coefficient given by:

![equation](https://latex.codecogs.com/svg.image?\Phi_j=\prod_{g\in&space;G_j}{\left\(\frac{\sum_{i\in&space;T_g}{t_i}}{\sum_{i\in&space;T}{t_i}}\cdot\frac{\sum_{i\in&space;S}{e^{u_i}}}{\sum_{i\in&space;S_g}{e^{u_i}}}\right\)})

Where Gj are the tags of task j (including the project), Sg is the set of pending tasks tagged with g, S is the set of all pending tags, Tg is the set of tasks with tagged with g with any time spent and T is the set of all tags with any tipe spent.

This coefficient is intended to balance the daily time spent on a tag according to the share remaining tasks should take.

## Edge cases

There are two edge cases: the one where a long task has the greatest urgency and remaining tasks can be sorted out in a short time and the other where a task has a urgency that doesn't allow task commutation

### Long task problem

If a long task has the greatest urgency and all the other tasks can be readily done, the greatest task will be started. On the first commutation event, this long task will have 100% of the executed time, so the second task will be selected. When this second task is marked as done, the long task would go back having 100% of executed time so it will be skipped again.

In order to overcome this issue, whenever the greatest urgency task has 100%, it will remain on this task except if the last recorded time is bigger than a configured value (typically 25min).

### High urgency task problem

In the event of a task with an urgency much greater than the rest, the next command would never indicate any commutation (except when there is a long task problem). When this happens, the next command will suggest a commutation to the task with the second greatest difference between *time spent* fraction and the ideal fraction if the time spent on the task is grater than a maximum time (typically 25min).
