"""
Background job processing service for long-running tasks
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import traceback
from concurrent.futures import ThreadPoolExecutor
import pickle

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobPriority(Enum):
    """Job priority levels"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class JobResult:
    """Job execution result"""

    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Job:
    """Background job definition"""

    id: str
    name: str
    function_name: str
    args: tuple
    kwargs: dict
    priority: JobPriority
    status: JobStatus
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    max_retries: int = 3
    retry_count: int = 0
    retry_delay: int = 60  # seconds
    timeout: Optional[int] = None  # seconds
    result: Optional[JobResult] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
            elif isinstance(value, (JobStatus, JobPriority)):
                data[key] = value.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        """Create job from dictionary"""
        # Convert ISO strings back to datetime objects
        datetime_fields = ["created_at", "scheduled_at", "started_at", "completed_at"]
        for field in datetime_fields:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])

        # Convert enum values
        if "status" in data:
            data["status"] = JobStatus(data["status"])
        if "priority" in data:
            data["priority"] = JobPriority(data["priority"])

        # Handle result
        if "result" in data and data["result"]:
            if isinstance(data["result"], dict):
                data["result"] = JobResult(**data["result"])

        return cls(**data)


class JobQueue:
    """Priority-based job queue"""

    def __init__(self):
        self.queues = {
            JobPriority.URGENT: asyncio.Queue(),
            JobPriority.HIGH: asyncio.Queue(),
            JobPriority.NORMAL: asyncio.Queue(),
            JobPriority.LOW: asyncio.Queue(),
        }
        self.lock = asyncio.Lock()

    async def put(self, job: Job):
        """Add job to appropriate priority queue"""
        await self.queues[job.priority].put(job)

    async def get(self) -> Job:
        """Get next job from highest priority queue"""
        # Check queues in priority order
        for priority in [
            JobPriority.URGENT,
            JobPriority.HIGH,
            JobPriority.NORMAL,
            JobPriority.LOW,
        ]:
            queue = self.queues[priority]
            if not queue.empty():
                return await queue.get()

        # If all queues are empty, wait for any job
        tasks = [asyncio.create_task(queue.get()) for queue in self.queues.values()]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # Cancel pending tasks
        for task in pending:
            task.cancel()

        # Return the first completed job
        return done.pop().result()

    def qsize(self) -> Dict[JobPriority, int]:
        """Get queue sizes"""
        return {priority: queue.qsize() for priority, queue in self.queues.items()}

    def empty(self) -> bool:
        """Check if all queues are empty"""
        return all(queue.empty() for queue in self.queues.values())


class BackgroundJobService:
    """Background job processing service"""

    def __init__(self, max_workers: int = 4, max_concurrent_jobs: int = 10):
        self.max_workers = max_workers
        self.max_concurrent_jobs = max_concurrent_jobs
        self.job_queue = JobQueue()
        self.active_jobs: Dict[str, Job] = {}
        self.completed_jobs: Dict[str, Job] = {}
        self.job_registry: Dict[str, Callable] = {}
        self.workers: List[asyncio.Task] = []
        self.running = False
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)

        # Job storage (in production, use Redis or database)
        self.job_storage: Dict[str, Job] = {}

        # Statistics
        self.stats = {
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "cancelled_jobs": 0,
            "average_execution_time": 0.0,
        }

    def register_job_function(self, name: str, func: Callable):
        """Register a function that can be executed as a background job"""
        self.job_registry[name] = func
        logger.info(f"Registered job function: {name}")

    async def start(self):
        """Start the background job service"""
        if self.running:
            return

        self.running = True

        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)

        # Start scheduler task
        scheduler = asyncio.create_task(self._scheduler())
        self.workers.append(scheduler)

        logger.info(f"Background job service started with {self.max_workers} workers")

    async def stop(self):
        """Stop the background job service"""
        if not self.running:
            return

        self.running = False

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)

        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)

        logger.info("Background job service stopped")

    async def submit_job(
        self,
        function_name: str,
        *args,
        priority: JobPriority = JobPriority.NORMAL,
        scheduled_at: Optional[datetime] = None,
        max_retries: int = 3,
        retry_delay: int = 60,
        timeout: Optional[int] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """Submit a job for background execution"""

        if function_name not in self.job_registry:
            raise ValueError(f"Unknown job function: {function_name}")

        job_id = str(uuid.uuid4())

        job = Job(
            id=job_id,
            name=function_name,
            function_name=function_name,
            args=args,
            kwargs=kwargs,
            priority=priority,
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
            scheduled_at=scheduled_at,
            max_retries=max_retries,
            retry_delay=retry_delay,
            timeout=timeout,
            user_id=user_id,
            session_id=session_id,
            metadata=metadata or {},
        )

        # Store job
        self.job_storage[job_id] = job

        # Add to queue if not scheduled for later
        if scheduled_at is None or scheduled_at <= datetime.utcnow():
            await self.job_queue.put(job)

        self.stats["total_jobs"] += 1

        logger.info(f"Submitted job {job_id}: {function_name}")
        return job_id

    async def get_job_status(self, job_id: str) -> Optional[Job]:
        """Get job status"""
        # Check active jobs first
        if job_id in self.active_jobs:
            return self.active_jobs[job_id]

        # Check completed jobs
        if job_id in self.completed_jobs:
            return self.completed_jobs[job_id]

        # Check storage
        return self.job_storage.get(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        job = await self.get_job_status(job_id)
        if not job:
            return False

        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False

        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()

        # Remove from active jobs if running
        if job_id in self.active_jobs:
            del self.active_jobs[job_id]

        # Move to completed jobs
        self.completed_jobs[job_id] = job
        self.stats["cancelled_jobs"] += 1

        logger.info(f"Cancelled job {job_id}")
        return True

    async def retry_job(self, job_id: str) -> bool:
        """Retry a failed job"""
        job = await self.get_job_status(job_id)
        if not job or job.status != JobStatus.FAILED:
            return False

        if job.retry_count >= job.max_retries:
            return False

        job.status = JobStatus.PENDING
        job.retry_count += 1
        job.started_at = None
        job.completed_at = None
        job.result = None

        # Re-queue the job
        await self.job_queue.put(job)

        logger.info(f"Retrying job {job_id} (attempt {job.retry_count + 1})")
        return True

    async def _worker(self, worker_name: str):
        """Worker task that processes jobs from the queue"""
        logger.info(f"Worker {worker_name} started")

        while self.running:
            try:
                # Get next job from queue
                job = await asyncio.wait_for(self.job_queue.get(), timeout=1.0)

                # Check if we have too many concurrent jobs
                if len(self.active_jobs) >= self.max_concurrent_jobs:
                    # Put job back in queue and wait
                    await self.job_queue.put(job)
                    await asyncio.sleep(1)
                    continue

                # Execute the job
                await self._execute_job(job, worker_name)

            except asyncio.TimeoutError:
                # No jobs available, continue
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(1)

        logger.info(f"Worker {worker_name} stopped")

    async def _scheduler(self):
        """Scheduler task that handles delayed jobs"""
        logger.info("Job scheduler started")

        while self.running:
            try:
                current_time = datetime.utcnow()

                # Check for scheduled jobs that are ready to run
                scheduled_jobs = [
                    job
                    for job in self.job_storage.values()
                    if (
                        job.status == JobStatus.PENDING
                        and job.scheduled_at
                        and job.scheduled_at <= current_time
                    )
                ]

                for job in scheduled_jobs:
                    await self.job_queue.put(job)
                    job.scheduled_at = None  # Clear scheduled time

                # Sleep for a short interval
                await asyncio.sleep(10)  # Check every 10 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(10)

        logger.info("Job scheduler stopped")

    async def _execute_job(self, job: Job, worker_name: str):
        """Execute a single job"""
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        self.active_jobs[job.id] = job

        logger.info(f"Worker {worker_name} executing job {job.id}: {job.name}")

        try:
            # Get the function to execute
            func = self.job_registry[job.function_name]

            # Execute the function
            start_time = datetime.utcnow()

            if asyncio.iscoroutinefunction(func):
                # Async function
                if job.timeout:
                    result = await asyncio.wait_for(
                        func(*job.args, **job.kwargs), timeout=job.timeout
                    )
                else:
                    result = await func(*job.args, **job.kwargs)
            else:
                # Sync function - run in thread pool
                if job.timeout:
                    result = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            self.thread_pool, func, *job.args
                        ),
                        timeout=job.timeout,
                    )
                else:
                    result = await asyncio.get_event_loop().run_in_executor(
                        self.thread_pool, func, *job.args
                    )

            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()

            # Job completed successfully
            job.status = JobStatus.COMPLETED
            job.completed_at = end_time
            job.result = JobResult(
                success=True, result=result, execution_time=execution_time
            )

            self.stats["completed_jobs"] += 1
            self._update_average_execution_time(execution_time)

            logger.info(f"Job {job.id} completed successfully in {execution_time:.2f}s")

        except asyncio.TimeoutError:
            # Job timed out
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.result = JobResult(
                success=False, error=f"Job timed out after {job.timeout} seconds"
            )

            self.stats["failed_jobs"] += 1
            logger.error(f"Job {job.id} timed out")

        except Exception as e:
            # Job failed
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.result = JobResult(
                success=False,
                error=str(e),
                metadata={"traceback": traceback.format_exc()},
            )

            self.stats["failed_jobs"] += 1
            logger.error(f"Job {job.id} failed: {e}")

            # Schedule retry if applicable
            if job.retry_count < job.max_retries:
                retry_job = Job(
                    id=str(uuid.uuid4()),
                    name=job.name,
                    function_name=job.function_name,
                    args=job.args,
                    kwargs=job.kwargs,
                    priority=job.priority,
                    status=JobStatus.PENDING,
                    created_at=datetime.utcnow(),
                    scheduled_at=datetime.utcnow() + timedelta(seconds=job.retry_delay),
                    max_retries=job.max_retries,
                    retry_count=job.retry_count + 1,
                    retry_delay=job.retry_delay,
                    timeout=job.timeout,
                    user_id=job.user_id,
                    session_id=job.session_id,
                    metadata=job.metadata,
                )

                self.job_storage[retry_job.id] = retry_job
                logger.info(f"Scheduled retry for job {job.id} as {retry_job.id}")

        finally:
            # Move job from active to completed
            if job.id in self.active_jobs:
                del self.active_jobs[job.id]
            self.completed_jobs[job.id] = job

    def _update_average_execution_time(self, execution_time: float):
        """Update average execution time statistic"""
        current_avg = self.stats["average_execution_time"]
        completed_count = self.stats["completed_jobs"]

        if completed_count == 1:
            self.stats["average_execution_time"] = execution_time
        else:
            # Calculate running average
            self.stats["average_execution_time"] = (
                current_avg * (completed_count - 1) + execution_time
            ) / completed_count

    def get_statistics(self) -> Dict[str, Any]:
        """Get job processing statistics"""
        queue_sizes = self.job_queue.qsize()

        return {
            **self.stats,
            "active_jobs": len(self.active_jobs),
            "queue_sizes": {
                priority.name: size for priority, size in queue_sizes.items()
            },
            "total_queued": sum(queue_sizes.values()),
            "workers": len(self.workers),
            "max_workers": self.max_workers,
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "running": self.running,
        }

    async def get_job_list(
        self,
        status: Optional[JobStatus] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Job]:
        """Get list of jobs with optional filtering"""

        all_jobs = list(self.job_storage.values())

        # Filter by status
        if status:
            all_jobs = [job for job in all_jobs if job.status == status]

        # Filter by user
        if user_id:
            all_jobs = [job for job in all_jobs if job.user_id == user_id]

        # Sort by creation time (newest first)
        all_jobs.sort(key=lambda x: x.created_at, reverse=True)

        return all_jobs[:limit]

    async def cleanup_completed_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up old completed jobs"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        jobs_to_remove = [
            job_id
            for job_id, job in self.completed_jobs.items()
            if (
                job.completed_at
                and job.completed_at < cutoff_time
                and job.status
                in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
            )
        ]

        for job_id in jobs_to_remove:
            del self.completed_jobs[job_id]
            if job_id in self.job_storage:
                del self.job_storage[job_id]

        logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")
        return len(jobs_to_remove)

    async def health_check(self) -> bool:
        """Perform health check for background job service"""
        try:
            # Check if service is running
            if not self.running:
                return False
                
            # Check if workers are available
            if self.max_workers <= 0:
                return False
                
            # Check if queue is accessible
            if not hasattr(self, 'job_queue'):
                return False
                
            # Check if job storage is accessible
            if not hasattr(self, 'job_storage'):
                return False
                
            # Check statistics functionality
            stats = self.get_statistics()
            if not isinstance(stats, dict):
                return False
                
            return True
        except Exception as e:
            logger.error(f"BackgroundJobService health check failed: {e}")
            return False

    async def restart(self):
        """Restart the background job service"""
        try:
            logger.info("Restarting background job service")
            await self.stop()
            await asyncio.sleep(1)  # Brief pause
            await self.start()
            logger.info("Background job service restarted successfully")
        except Exception as e:
            logger.error(f"Failed to restart background job service: {e}")
            raise


# Predefined job functions for common tasks


async def optimize_resume_job(
    resume_data: Dict[str, Any], job_description: str
) -> Dict[str, Any]:
    """Background job for resume optimization"""
    # Import here to avoid circular imports
    from services.llm_provider import LLMProviderFactory
    from configs.config import get_config

    config = get_config()
    provider = LLMProviderFactory.create(config.llm_provider, config.llm_config)

    # Simulate long-running optimization
    await asyncio.sleep(2)  # Simulate processing time

    optimized_resume = await provider.optimize_resume(resume_data, job_description)

    return {
        "original_resume": resume_data,
        "optimized_resume": optimized_resume,
        "job_description": job_description,
        "optimization_timestamp": datetime.utcnow().isoformat(),
    }


async def analyze_job_description_job(job_description: str) -> Dict[str, Any]:
    """Background job for job description analysis"""
    from services.job_matcher import JobMatcher

    job_matcher = JobMatcher()

    # Simulate analysis time
    await asyncio.sleep(1)

    analysis = await job_matcher.analyze_job_description(job_description)

    return {
        "job_description": job_description,
        "analysis": analysis,
        "analysis_timestamp": datetime.utcnow().isoformat(),
    }


async def generate_resume_versions_job(
    resume_data: Dict[str, Any], job_descriptions: List[str]
) -> Dict[str, Any]:
    """Background job for generating multiple resume versions"""
    from services.version_manager import VersionManager

    version_manager = VersionManager()

    versions = []
    for i, job_desc in enumerate(job_descriptions):
        # Simulate processing time
        await asyncio.sleep(1)

        version = await version_manager.create_version(
            resume_data, f"Version for Job {i+1}", f"Optimized for: {job_desc[:100]}..."
        )
        versions.append(version)

    return {
        "original_resume": resume_data,
        "generated_versions": versions,
        "job_descriptions": job_descriptions,
        "generation_timestamp": datetime.utcnow().isoformat(),
    }


def export_resume_job(resume_data: Dict[str, Any], format: str) -> Dict[str, Any]:
    """Synchronous job for resume export"""
    from services.resume_generator import generate_resume
    import time

    # Simulate export time
    time.sleep(2)

    exported_file = generate_resume(resume_data, format)

    return {
        "resume_data": resume_data,
        "format": format,
        "exported_file": exported_file,
        "export_timestamp": datetime.utcnow().isoformat(),
    }


# Global background job service instance
_job_service: Optional[BackgroundJobService] = None


def get_job_service() -> BackgroundJobService:
    """Get the global background job service instance"""
    global _job_service
    if _job_service is None:
        _job_service = BackgroundJobService()
    return _job_service


async def initialize_job_service(max_workers: int = 4, max_concurrent_jobs: int = 10):
    """Initialize the global background job service"""
    global _job_service
    _job_service = BackgroundJobService(max_workers, max_concurrent_jobs)

    # Register common job functions
    _job_service.register_job_function("optimize_resume", optimize_resume_job)
    _job_service.register_job_function(
        "analyze_job_description", analyze_job_description_job
    )
    _job_service.register_job_function(
        "generate_resume_versions", generate_resume_versions_job
    )
    _job_service.register_job_function("export_resume", export_resume_job)

    await _job_service.start()


async def shutdown_job_service():
    """Shutdown the global background job service"""
    global _job_service
    if _job_service:
        await _job_service.stop()
        _job_service = None
